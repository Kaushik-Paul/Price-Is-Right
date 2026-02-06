import logging
import queue
import re
import threading
import time
import gradio as gr
from deal_agent_framework import DealAgentFramework
from log_utils import reformat
from rate_limiter import RateLimiter
import plotly.graph_objects as go

# Email validation regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class QueueHandler(logging.Handler):
    """Custom logging handler that puts log records into a queue."""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


def html_for(log_data):
    """Format log data as HTML for display."""
    output = "<br>".join(log_data[-18:])
    return f"""
    <div id="scrollContent" style="
        height: 400px; 
        overflow-y: auto; 
        border: 2px solid transparent;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        background-clip: padding-box;
        border-radius: 12px;
        padding: 16px;
        font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
        font-size: 13px;
        line-height: 1.6;
        color: #e2e8f0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        position: relative;
    ">
    <div style="
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        border-radius: 14px;
        z-index: -1;
        opacity: 0.6;
    "></div>
    {output}
    </div>
    """


def setup_logging(log_queue):
    """Set up logging with the queue handler."""
    handler = QueueHandler(log_queue)
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def is_valid_email(email: str) -> bool:
    """Validate email using regex."""
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


class GradioUI:
    """Gradio-based user interface for the Price is Right application."""
    
    def __init__(self, agent_framework: DealAgentFramework):
        self.agent_framework = agent_framework
        self.rate_limiter = RateLimiter()

    def _table_for(self, opps, highlight_index=None):
        """Convert opportunities to table format, sorted by date (latest first)."""
        # Sort by added_at timestamp (latest first), handling None values
        sorted_opps = sorted(
            opps, 
            key=lambda opp: opp.added_at or "1970-01-01", 
            reverse=True
        )
        
        rows = []
        for i, opp in enumerate(sorted_opps):
            # Format the date nicely if available
            date_str = ""
            if opp.added_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(opp.added_at)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = opp.added_at[:16] if len(opp.added_at) > 16 else opp.added_at
            
            # Check if this is the newly added deal (it will be first after sorting)
            is_new = (i == 0 and highlight_index is not None)
            indicator = "🆕 NEW" if is_new else ""
            
            rows.append([
                indicator,
                opp.deal.product_description,
                f"${opp.deal.price:.2f}",
                f"${opp.estimate:.2f}",
                f"${opp.discount:.2f}",
                date_str,
                f"[View Deal]({opp.deal.url})",  # Markdown link format for clickable URL
            ])
        return rows

    def _update_output(self, log_data, log_queue, result_queue, email, had_new_deal):
        """Generator that yields log updates and results."""
        initial_result = self._table_for(self.agent_framework.memory)
        final_result = None
        while True:
            try:
                message = log_queue.get_nowait()
                log_data.append(reformat(message))
                yield log_data, html_for(log_data), final_result or initial_result, gr.update(interactive=False), ""
            except queue.Empty:
                try:
                    final_result = result_queue.get_nowait()
                    # Re-enable button and show status after completion
                    status = self.rate_limiter.get_status_message()
                    yield log_data, html_for(log_data), final_result, gr.update(interactive=True), status
                except queue.Empty:
                    if final_result is not None:
                        break
                    time.sleep(0.1)

    def _get_plot(self):
        """Generate the 3D scatter plot visualization."""
        documents, vectors, colors = DealAgentFramework.get_plot_data(max_datapoints=800)
        
        # If no data is returned, show an empty plot with a message
        if not documents or len(vectors) == 0:
            fig = go.Figure()
            fig.update_layout(
                title="No deal data available yet for visualization.",
                height=400,
            )
            return fig

        # Create the 3D scatter plot
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=vectors[:, 0],
                    y=vectors[:, 1],
                    z=vectors[:, 2],
                    mode="markers",
                    marker=dict(size=2, color=colors, opacity=0.7),
                )
            ]
        )

        fig.update_layout(
            scene=dict(
                xaxis_title="x",
                yaxis_title="y",
                zaxis_title="z",
                aspectmode="manual",
                aspectratio=dict(x=2.2, y=2.2, z=1),
                camera=dict(
                    eye=dict(x=1.6, y=1.6, z=0.8)
                ),
                bgcolor="rgba(26, 26, 62, 0.8)",
                xaxis=dict(gridcolor="rgba(102, 126, 234, 0.2)", color="#a0aec0"),
                yaxis=dict(gridcolor="rgba(102, 126, 234, 0.2)", color="#a0aec0"),
                zaxis=dict(gridcolor="rgba(102, 126, 234, 0.2)", color="#a0aec0"),
            ),
            height=400,
            margin=dict(r=5, b=1, l=5, t=2),
            paper_bgcolor="rgba(26, 26, 62, 0.6)",
            plot_bgcolor="rgba(26, 26, 62, 0.6)",
        )

        return fig

    def _do_run(self, email: str = None):
        """Execute the agent framework and return table data."""
        # Store email in framework for messaging agent to use
        self.agent_framework.user_email = email
        memory_before = len(self.agent_framework.memory)
        new_opportunities = self.agent_framework.run()
        # Check if a new deal was added
        had_new_deal = len(new_opportunities) > memory_before
        # Highlight the first row if a new deal was added (since sorted latest first)
        table = self._table_for(new_opportunities, highlight_index=0 if had_new_deal else None)
        return table

    def _validate_email(self, email: str):
        """Validate email and return button state + status message."""
        if is_valid_email(email):
            status = self.rate_limiter.get_status_message()
            return gr.update(interactive=True), status
        else:
            if email and email.strip():
                return gr.update(interactive=False), '''
                    <div style="display: flex; align-items: center; justify-content: center; gap: 8px; 
                                padding: 10px 16px; background: rgba(255, 107, 107, 0.1); 
                                border: 1px solid rgba(255, 107, 107, 0.3); border-radius: 8px;">
                        <span style="color: #ff6b6b; font-weight: 500;">⚠️ Please enter a valid email address</span>
                    </div>
                '''
            else:
                return gr.update(interactive=False), '''
                    <div style="display: flex; align-items: center; justify-content: center; gap: 8px; 
                                padding: 10px 16px; background: rgba(102, 126, 234, 0.1); 
                                border: 1px solid rgba(102, 126, 234, 0.2); border-radius: 8px;">
                        <span style="color: #a0aec0;">📧 Enter your email to enable the Hunt for Deals button</span>
                    </div>
                '''

    def _run_with_logging(self, initial_log_data, email):
        """Run the agent with logging support."""
        # First check rate limit
        can_run, remaining = self.rate_limiter.can_run()
        if not can_run:
            error_msg = f'''
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px; 
                            padding: 12px 16px; background: rgba(255, 107, 107, 0.15); 
                            border: 1px solid rgba(255, 107, 107, 0.4); border-radius: 8px;">
                    <span style="color: #ff6b6b; font-weight: 600;">⚠️ Daily limit reached! Maximum {self.rate_limiter.MAX_DAILY_RUNS} runs per day allowed. Resets at 12 AM IST.</span>
                </div>
            '''
            yield initial_log_data, html_for(initial_log_data), self._table_for(self.agent_framework.memory), gr.update(interactive=True), error_msg
            return
        
        # Validate email with regex
        if not is_valid_email(email):
            error_msg = '''
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px; 
                            padding: 12px 16px; background: rgba(255, 107, 107, 0.15); 
                            border: 1px solid rgba(255, 107, 107, 0.4); border-radius: 8px;">
                    <span style="color: #ff6b6b; font-weight: 600;">⚠️ Please enter a valid email address.</span>
                </div>
            '''
            yield initial_log_data, html_for(initial_log_data), self._table_for(self.agent_framework.memory), gr.update(interactive=True), error_msg
            return
        
        email = email.strip()
        
        log_queue = queue.Queue()
        result_queue = queue.Queue()
        setup_logging(log_queue)
        memory_before = len(self.agent_framework.memory)

        def worker():
            result = self._do_run(email)
            # Increment rate limit counter after successful run
            self.rate_limiter.increment_run_count()
            result_queue.put(result)

        thread = threading.Thread(target=worker)
        thread.start()

        had_new_deal = len(self.agent_framework.memory) > memory_before
        for log_data, output, final_result, button_state, status in self._update_output(
            initial_log_data, log_queue, result_queue, email, had_new_deal
        ):
            yield log_data, output, final_result, button_state, status

    def _do_select(self, selected_index: gr.SelectData):
        """Handle row selection in the dataframe."""
        opportunities = self.agent_framework.memory
        row = selected_index.index[0]
        opportunity = opportunities[row]
        self.agent_framework.planner.messenger.alert(opportunity)

    def _get_initial_status(self):
        """Get the initial status message for rate limiting."""
        return '''
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; 
                        padding: 10px 16px; background: rgba(102, 126, 234, 0.1); 
                        border: 1px solid rgba(102, 126, 234, 0.2); border-radius: 8px;">
                <span style="color: #a0aec0;">📧 Enter your email to enable the Hunt for Deals button</span>
            </div>
        '''

    def build(self) -> gr.Blocks:
        """Build and return the Gradio UI."""
        # Custom CSS for modern, visually appealing design
        custom_css = """
        /* Global styles and dark theme */
        .gradio-container {
            background: linear-gradient(135deg, #0c0c1e 0%, #1a1a3e 50%, #0d1b2a 100%) !important;
            min-height: 100vh;
        }
        
        /* Main title styling */
        .main-title {
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.5rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px;
            margin-bottom: 0 !important;
            text-shadow: 0 0 40px rgba(102, 126, 234, 0.3);
        }
        
        .subtitle {
            text-align: center;
            color: #a0aec0 !important;
            font-size: 1rem !important;
            font-weight: 400;
            margin-top: 8px !important;
            line-height: 1.6;
        }
        
        /* Section headers */
        .section-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            background: linear-gradient(90deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.05) 100%);
            border-left: 4px solid #667eea;
            border-radius: 0 8px 8px 0;
            margin: 20px 0 12px 0;
        }
        
        .section-header h3 {
            margin: 0 !important;
            color: #e2e8f0 !important;
            font-size: 1.1rem !important;
            font-weight: 600 !important;
        }
        
        .section-icon {
            font-size: 1.3rem;
        }
        
        /* Card styling for sections */
        .card-container {
            background: rgba(26, 26, 62, 0.6);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(102, 126, 234, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }
        
        /* Input field styling */
        .gradio-textbox input {
            background: rgba(26, 26, 62, 0.8) !important;
            border: 2px solid rgba(102, 126, 234, 0.3) !important;
            border-radius: 12px !important;
            color: #e2e8f0 !important;
            padding: 14px 18px !important;
            font-size: 1rem !important;
            transition: all 0.3s ease !important;
        }
        
        .gradio-textbox input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3) !important;
            outline: none !important;
        }
        
        .gradio-textbox input::placeholder {
            color: #718096 !important;
        }
        
        .gradio-textbox label {
            color: #a0aec0 !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
        }
        
        /* Primary button styling */
        .primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            border: none !important;
            border-radius: 12px !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 14px 28px !important;
            font-size: 1rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
        }
        
        .primary:hover:not(:disabled) {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5) !important;
        }
        
        .primary:disabled {
            opacity: 0.5 !important;
            cursor: not-allowed !important;
        }
        
        /* Dataframe styling */
        .gradio-dataframe {
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
        }
        
        .gradio-dataframe table {
            background: rgba(26, 26, 62, 0.8) !important;
        }
        
        .gradio-dataframe th {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%) !important;
            color: #e2e8f0 !important;
            font-weight: 600 !important;
            padding: 14px 12px !important;
            text-transform: uppercase !important;
            font-size: 0.75rem !important;
            letter-spacing: 0.5px !important;
        }
        
        .gradio-dataframe td {
            color: #cbd5e0 !important;
            padding: 12px !important;
            border-bottom: 1px solid rgba(102, 126, 234, 0.1) !important;
        }
        
        .gradio-dataframe tr:hover td {
            background: rgba(102, 126, 234, 0.1) !important;
        }
        
        /* Plot container */
        .gradio-plot {
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            background: rgba(26, 26, 62, 0.6) !important;
        }
        
        /* Status message styling */
        .status-message {
            text-align: center;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
        }
        
        /* Footer styling */
        footer {
            display: none !important;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .main-title {
                font-size: 1.8rem !important;
            }
            .subtitle {
                font-size: 0.9rem !important;
            }
        }
        """
        
        with gr.Blocks(title="The Price is Right", fill_width=True, css=custom_css, theme=gr.themes.Soft(
            primary_hue=gr.themes.colors.purple,
            secondary_hue=gr.themes.colors.indigo,
            neutral_hue=gr.themes.colors.slate,
        )) as ui:
            log_data = gr.State([])

            # Header section with elegant title
            gr.HTML("""
                <div style="text-align: center; padding: 30px 20px 10px 20px;">
                    <h1 class="main-title">💰 The Price is Right</h1>
                    <p class="subtitle">
                        An Autonomous Agent Framework powered by a fine-tuned LLM and RAG pipeline<br>
                        <span style="color: #667eea;">✨ Discover incredible deals • 📬 Get instant notifications • 🤖 AI-driven analysis</span>
                    </p>
                </div>
            """)
            
            # Email & Action Section
            gr.HTML("""
                <div class="section-header">
                    <span class="section-icon">📧</span>
                    <h3>Get Deal Alerts</h3>
                </div>
            """)
            
            with gr.Row():
                email_input = gr.Textbox(
                    label="Email Address",
                    placeholder="📮 Enter your email to receive deal notifications...",
                    scale=3,
                    container=True
                )
                run_button = gr.Button("🚀 Hunt for Deals", variant="primary", scale=1, interactive=False)
            
            # Status message for rate limiting
            with gr.Row():
                status_message = gr.HTML(value=self._get_initial_status())
            
            # Deals Section
            gr.HTML("""
                <div class="section-header">
                    <span class="section-icon">🏷️</span>
                    <h3>Discovered Deals</h3>
                </div>
            """)
            
            with gr.Row():
                opportunities_dataframe = gr.Dataframe(
                    headers=["", "Deal Description", "Price", "Estimate", "Discount", "Date Added", "URL"],
                    datatype=["str", "str", "str", "str", "str", "str", "markdown"],  # Enable markdown for URL column
                    wrap=True,
                    column_widths=[1, 5, 1, 1, 1, 2, 2],
                    row_count=10,
                    col_count=7,
                    max_height=400,
                )
            
            # Analytics Section
            gr.HTML("""
                <div class="section-header">
                    <span class="section-icon">📊</span>
                    <h3>Agent Analytics</h3>
                </div>
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("""
                        <div style="color: #a0aec0; font-size: 0.85rem; margin-bottom: 8px; font-weight: 500;">
                            🔄 Live Agent Logs
                        </div>
                    """)
                    logs = gr.HTML()
                with gr.Column(scale=1):
                    gr.HTML("""
                        <div style="color: #a0aec0; font-size: 0.85rem; margin-bottom: 8px; font-weight: 500;">
                            📈 Deal Embeddings Visualization
                        </div>
                    """)
                    plot = gr.Plot(value=self._get_plot(), show_label=False)

            # Validate email on input change to enable/disable button
            email_input.change(
                self._validate_email,
                inputs=[email_input],
                outputs=[run_button, status_message],
            )

            # Connect Run button to workflow (replaces timer)
            run_button.click(
                self._run_with_logging,
                inputs=[log_data, email_input],
                outputs=[log_data, logs, opportunities_dataframe, run_button, status_message],
            )

            opportunities_dataframe.select(self._do_select)

        return ui

    def launch(self, **kwargs):
        """Build and launch the Gradio UI."""
        ui = self.build()
        ui.launch(**kwargs)
