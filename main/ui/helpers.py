"""
Helper functions and utilities for the Gradio UI.
"""

import logging
import re
import queue
import numpy as np
import plotly.graph_objects as go
from log_utils import reformat

# Email validation regex pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class QueueHandler(logging.Handler):
    """Custom logging handler that puts log records into a queue."""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


def setup_logging(log_queue: queue.Queue) -> None:
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


def html_for_logs(log_data: list) -> str:
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


def create_3d_plot(documents: list, vectors: np.ndarray, colors: list, categories: list = None) -> go.Figure:
    """Create the 3D scatter plot visualization for deal embeddings.
    
    Args:
        documents: List of product descriptions
        vectors: Numpy array of 3D coordinates after t-SNE reduction
        colors: List of color strings for each point
        categories: List of category names for each point (optional)
    """
    # If no data is returned, show an empty plot with a message
    if not documents or len(vectors) == 0:
        fig = go.Figure()
        fig.update_layout(
            title="No deal data available yet for visualization.",
            height=400,
        )
        return fig

    # Prepare hover text based on categories
    if categories:
        # Format category names to be more readable
        formatted_categories = [cat.replace("_", " ") for cat in categories]
        # Clean and truncate product descriptions for concise hover
        clean_docs = [doc.replace("Title: ", "", 1) if doc.startswith("Title: ") else doc for doc in documents]
        truncated_docs = [doc[:15] + "..." if len(doc) > 15 else doc for doc in clean_docs]
        hover_text = [f"<b>Category:</b> {cat}<br><b>Product:</b> {doc}" 
                      for cat, doc in zip(formatted_categories, truncated_docs)]
    else:
        hover_text = documents

    # Create the 3D scatter plot
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=vectors[:, 0],
                y=vectors[:, 1],
                z=vectors[:, 2],
                mode="markers",
                marker=dict(size=2, color=colors, opacity=0.7),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
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


def format_opportunity_row(opp, is_new: bool = False) -> list:
    """Format a single opportunity as a table row.
    
    Args:
        opp: Opportunity object
        is_new: Whether this is a newly added deal
        
    Returns:
        List of formatted cell values for the row
    """
    from datetime import datetime
    
    # Format the date nicely if available
    date_str = ""
    if opp.added_at:
        try:
            dt = datetime.fromisoformat(opp.added_at)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = opp.added_at[:16] if len(opp.added_at) > 16 else opp.added_at
    
    indicator = "🔥✨ HOT DEAL" if is_new else ""
    
    return [
        indicator,
        opp.deal.product_description,
        f"${opp.deal.price:.2f}",
        f"${opp.estimate:.2f}",
        f"${opp.discount:.2f}",
        date_str,
        f"[View Deal]({opp.deal.url})",  # Markdown link format for clickable URL
    ]
