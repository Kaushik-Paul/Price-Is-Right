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
    <div id="scrollContent" style="height: 400px; overflow-y: auto; border: 1px solid #ccc; background-color: #222229; padding: 10px;">
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
                opp.deal.url,
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
            ),
            height=400,
            margin=dict(r=5, b=1, l=5, t=2),
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
                return gr.update(interactive=False), '<div style="color: #ff6b6b;">⚠️ Please enter a valid email address</div>'
            else:
                return gr.update(interactive=False), '<div style="color: #888;">Enter your email to enable the Run button</div>'

    def _run_with_logging(self, initial_log_data, email):
        """Run the agent with logging support."""
        # First check rate limit
        can_run, remaining = self.rate_limiter.can_run()
        if not can_run:
            error_msg = f'<div style="color: #ff6b6b; font-weight: bold;">⚠️ Daily limit reached! Maximum {self.rate_limiter.MAX_DAILY_RUNS} runs per day allowed. Resets at 12 AM IST.</div>'
            yield initial_log_data, html_for(initial_log_data), self._table_for(self.agent_framework.memory), gr.update(interactive=True), error_msg
            return
        
        # Validate email with regex
        if not is_valid_email(email):
            error_msg = '<div style="color: #ff6b6b; font-weight: bold;">⚠️ Please enter a valid email address.</div>'
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
        return '<div style="color: #888;">Enter your email to enable the Run button</div>'

    def build(self) -> gr.Blocks:
        """Build and return the Gradio UI."""
        with gr.Blocks(title="The Price is Right", fill_width=True) as ui:
            log_data = gr.State([])

            with gr.Row():
                gr.Markdown(
                    '<div style="text-align: center;font-size:24px"><strong>The Price is Right</strong> - Autonomous Agent Framework that hunts for deals</div>'
                )
            with gr.Row():
                gr.Markdown(
                    '<div style="text-align: center;font-size:14px">A proprietary fine-tuned LLM deployed on Modal and a RAG pipeline with a frontier model collaborate to send push notifications with great online deals.</div>'
                )
            
            # Email input and Run button row
            with gr.Row():
                email_input = gr.Textbox(
                    label="Email for Deal Alerts",
                    placeholder="Enter your email to receive deal notifications",
                    scale=3
                )
                run_button = gr.Button("🚀 Run Workflow", variant="primary", scale=1, interactive=False)
            
            # Status message for rate limiting
            with gr.Row():
                status_message = gr.HTML(value=self._get_initial_status())
            
            with gr.Row():
                opportunities_dataframe = gr.Dataframe(
                    headers=["", "Deal Description", "Price", "Estimate", "Discount", "Date Added", "URL"],
                    wrap=True,
                    column_widths=[1, 5, 1, 1, 1, 2, 3],
                    row_count=10,
                    col_count=7,
                    max_height=400,
                )
            with gr.Row():
                with gr.Column(scale=1):
                    logs = gr.HTML()
                with gr.Column(scale=1):
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
