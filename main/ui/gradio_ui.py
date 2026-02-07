"""
Gradio-based user interface for the Price is Right application.

This module provides the main UI class that builds and manages the Gradio interface.
CSS styles are imported from styles.py and helper functions from helpers.py.
"""

import queue
import threading
import time
import gradio as gr
from deal_agent_framework import DealAgentFramework
from rate_limiter import RateLimiter

# Import styles and templates
from ui.styles import (
    CUSTOM_CSS,
    HEADER_HTML,
    EMAIL_SECTION_HEADER,
    DEALS_SECTION_HEADER,
    ANALYTICS_SECTION_HEADER,
    LOGS_LABEL,
    PLOT_LABEL,
    get_status_html,
)

# Import helper functions
from ui.helpers import (
    setup_logging,
    is_valid_email,
    html_for_logs,
    create_3d_plot,
    format_opportunity_row,
)


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
            # Check if this is the newly added deal (it will be first after sorting)
            is_new = (i == 0 and highlight_index is not None)
            rows.append(format_opportunity_row(opp, is_new=is_new))
        return rows

    def _update_output(self, log_data, log_queue, result_queue, email, had_new_deal):
        """Generator that yields log updates and results."""
        from log_utils import reformat
        
        initial_result = self._table_for(self.agent_framework.memory)
        final_result = None
        while True:
            try:
                message = log_queue.get_nowait()
                log_data.append(reformat(message))
                yield log_data, html_for_logs(log_data), final_result or initial_result, gr.update(interactive=False), ""
            except queue.Empty:
                try:
                    final_result = result_queue.get_nowait()
                    # Re-enable button and show status after completion
                    status = self.rate_limiter.get_status_message()
                    yield log_data, html_for_logs(log_data), final_result, gr.update(interactive=True), status
                except queue.Empty:
                    if final_result is not None:
                        break
                    time.sleep(0.1)

    def _get_plot(self):
        """Generate the 3D scatter plot visualization."""
        documents, vectors, colors, categories = DealAgentFramework.get_plot_data(max_datapoints=800)
        return create_3d_plot(documents, vectors, colors, categories)

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
                return gr.update(interactive=False), get_status_html(
                    "⚠️ Please enter a valid email address", 
                    style="error"
                )
            else:
                return gr.update(interactive=False), get_status_html(
                    "📧 Enter your email to enable the Hunt for Deals button",
                    style="info"
                )

    def _run_with_logging(self, initial_log_data, email):
        """Run the agent with logging support."""
        # First check rate limit
        can_run, remaining = self.rate_limiter.can_run()
        if not can_run:
            error_msg = get_status_html(
                f"⚠️ Daily limit reached! Maximum {self.rate_limiter.MAX_DAILY_RUNS} runs per day allowed. Resets at 12 AM IST.",
                style="error"
            )
            yield initial_log_data, html_for_logs(initial_log_data), self._table_for(self.agent_framework.memory), gr.update(interactive=True), error_msg
            return
        
        # Validate email with regex
        if not is_valid_email(email):
            error_msg = get_status_html(
                "⚠️ Please enter a valid email address.",
                style="error"
            )
            yield initial_log_data, html_for_logs(initial_log_data), self._table_for(self.agent_framework.memory), gr.update(interactive=True), error_msg
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
        return get_status_html(
            "📧 Enter your email to enable the Hunt for Deals button",
            style="info"
        )

    def build(self) -> gr.Blocks:
        """Build and return the Gradio UI."""
        with gr.Blocks(
            title="The Price is Right",
            fill_width=True,
        ) as ui:
            log_data = gr.State([])

            # Header section with elegant title
            gr.HTML(HEADER_HTML)
            
            # Email & Action Section
            gr.HTML(EMAIL_SECTION_HEADER)
            
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
            gr.HTML(DEALS_SECTION_HEADER)
            
            with gr.Row():
                opportunities_dataframe = gr.Dataframe(
                    headers=["", "Deal Description", "Price", "Estimate", "Discount", "Date Added", "URL"],
                    datatype=["str", "str", "str", "str", "str", "str", "markdown"],
                    wrap=True,
                    column_widths=[1, 5, 1, 1, 1, 2, 2],
                    row_count=10,
                    column_count=7,
                    max_height=400,
                )
            
            # Analytics Section
            gr.HTML(ANALYTICS_SECTION_HEADER)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML(LOGS_LABEL)
                    logs = gr.HTML()
                with gr.Column(scale=1):
                    gr.HTML(PLOT_LABEL)
                    plot = gr.Plot(value=self._get_plot(), show_label=False)

            # Event handlers
            email_input.change(
                self._validate_email,
                inputs=[email_input],
                outputs=[run_button, status_message],
            )

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
        ui.launch(
            css=CUSTOM_CSS,
            theme=gr.themes.Soft(
                primary_hue=gr.themes.colors.purple,
                secondary_hue=gr.themes.colors.indigo,
                neutral_hue=gr.themes.colors.slate,
            ),
            **kwargs
        )
