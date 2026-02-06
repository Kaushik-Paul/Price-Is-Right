import logging
import queue
import threading
import time
import gradio as gr
from deal_agent_framework import DealAgentFramework
from log_utils import reformat
import plotly.graph_objects as go


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


class GradioUI:
    """Gradio-based user interface for the Price is Right application."""
    
    def __init__(self, agent_framework: DealAgentFramework):
        self.agent_framework = agent_framework

    def _table_for(self, opps):
        """Convert opportunities to table format."""
        return [
            [
                opp.deal.product_description,
                f"${opp.deal.price:.2f}",
                f"${opp.estimate:.2f}",
                f"${opp.discount:.2f}",
                opp.deal.url,
            ]
            for opp in opps
        ]

    def _update_output(self, log_data, log_queue, result_queue):
        """Generator that yields log updates and results."""
        initial_result = self._table_for(self.agent_framework.memory)
        final_result = None
        while True:
            try:
                message = log_queue.get_nowait()
                log_data.append(reformat(message))
                yield log_data, html_for(log_data), final_result or initial_result
            except queue.Empty:
                try:
                    final_result = result_queue.get_nowait()
                    yield log_data, html_for(log_data), final_result or initial_result
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

    def _do_run(self):
        """Execute the agent framework and return table data."""
        new_opportunities = self.agent_framework.run()
        table = self._table_for(new_opportunities)
        return table

    def _run_with_logging(self, initial_log_data):
        """Run the agent with logging support."""
        log_queue = queue.Queue()
        result_queue = queue.Queue()
        setup_logging(log_queue)

        def worker():
            result = self._do_run()
            result_queue.put(result)

        thread = threading.Thread(target=worker)
        thread.start()

        for log_data, output, final_result in self._update_output(
            initial_log_data, log_queue, result_queue
        ):
            yield log_data, output, final_result

    def _do_select(self, selected_index: gr.SelectData):
        """Handle row selection in the dataframe."""
        opportunities = self.agent_framework.memory
        row = selected_index.index[0]
        opportunity = opportunities[row]
        self.agent_framework.planner.messenger.alert(opportunity)

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
            with gr.Row():
                opportunities_dataframe = gr.Dataframe(
                    headers=["Deals found so far", "Price", "Estimate", "Discount", "URL"],
                    wrap=True,
                    column_widths=[6, 1, 1, 1, 3],
                    row_count=10,
                    col_count=5,
                    max_height=400,
                )
            with gr.Row():
                with gr.Column(scale=1):
                    logs = gr.HTML()
                with gr.Column(scale=1):
                    plot = gr.Plot(value=self._get_plot(), show_label=False)

            ui.load(
                self._run_with_logging,
                inputs=[log_data],
                outputs=[log_data, logs, opportunities_dataframe],
            )

            timer = gr.Timer(value=300, active=True)
            timer.tick(
                self._run_with_logging,
                inputs=[log_data],
                outputs=[log_data, logs, opportunities_dataframe],
            )

            opportunities_dataframe.select(self._do_select)

        return ui

    def launch(self, **kwargs):
        """Build and launch the Gradio UI."""
        ui = self.build()
        ui.launch(**kwargs)
