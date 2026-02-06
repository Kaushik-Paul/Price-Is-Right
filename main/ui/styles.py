"""
CSS styles for the Gradio UI.
"""

# Custom CSS for modern, visually appealing design
CUSTOM_CSS = """
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

/* Dataframe styling - CLEAN AND READABLE */
.gradio-dataframe {
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid #4a5568 !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
}

.gradio-dataframe table {
    background: #1a202c !important;
    border-collapse: collapse !important;
    width: 100% !important;
}

.gradio-dataframe th {
    background: #2d3748 !important;
    color: #fff !important;
    font-weight: 600 !important;
    padding: 14px 16px !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    border-bottom: 2px solid #4a5568 !important;
    text-align: left !important;
}

.gradio-dataframe td {
    color: #e2e8f0 !important;
    padding: 14px 16px !important;
    border-bottom: 1px solid #4a5568 !important;
    font-size: 0.9rem !important;
    line-height: 1.5 !important;
}

.gradio-dataframe tr:nth-child(odd) td {
    background: #1a202c !important;
}

.gradio-dataframe tr:nth-child(even) td {
    background: #2d3748 !important;
}

.gradio-dataframe tr:hover td {
    background: #3d4a5c !important;
}

/* Hot deal indicator styling */
.gradio-dataframe td:first-child {
    font-weight: 700 !important;
    color: #fc8181 !important;
    white-space: nowrap !important;
}

/* URL column styling */
.gradio-dataframe td:last-child a {
    color: #90cdf4 !important;
    text-decoration: none !important;
}

.gradio-dataframe td:last-child a:hover {
    color: #63b3ed !important;
    text-decoration: underline !important;
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


# HTML Templates
HEADER_HTML = """
<div style="text-align: center; padding: 30px 20px 10px 20px;">
    <h1 class="main-title">💰 The Price is Right</h1>
    <p class="subtitle">
        An Autonomous Agent Framework powered by a fine-tuned LLM and RAG pipeline<br>
        <span style="color: #667eea;">✨ Discover incredible deals • 📬 Get instant notifications • 🤖 AI-driven analysis</span>
    </p>
</div>
"""

EMAIL_SECTION_HEADER = """
<div class="section-header">
    <span class="section-icon">📧</span>
    <h3>Get Deal Alerts</h3>
</div>
"""

DEALS_SECTION_HEADER = """
<div class="section-header">
    <span class="section-icon">🏷️</span>
    <h3>Discovered Deals</h3>
</div>
"""

ANALYTICS_SECTION_HEADER = """
<div class="section-header">
    <span class="section-icon">📊</span>
    <h3>Agent Analytics</h3>
</div>
"""

LOGS_LABEL = """
<div style="color: #a0aec0; font-size: 0.85rem; margin-bottom: 8px; font-weight: 500;">
    🔄 Live Agent Logs
</div>
"""

PLOT_LABEL = """
<div style="color: #a0aec0; font-size: 0.85rem; margin-bottom: 8px; font-weight: 500;">
    📈 Deal Embeddings Visualization
</div>
"""


def get_status_html(message: str, style: str = "info") -> str:
    """Generate styled status HTML message.
    
    Args:
        message: The message to display
        style: One of 'info', 'error', or 'success'
    """
    styles = {
        "info": {
            "bg": "rgba(102, 126, 234, 0.1)",
            "border": "rgba(102, 126, 234, 0.2)",
            "color": "#a0aec0"
        },
        "error": {
            "bg": "rgba(255, 107, 107, 0.15)",
            "border": "rgba(255, 107, 107, 0.4)",
            "color": "#ff6b6b"
        },
        "success": {
            "bg": "rgba(72, 187, 120, 0.15)",
            "border": "rgba(72, 187, 120, 0.4)",
            "color": "#48bb78"
        }
    }
    
    s = styles.get(style, styles["info"])
    
    return f'''
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px; 
                    padding: 10px 16px; background: {s["bg"]}; 
                    border: 1px solid {s["border"]}; border-radius: 8px;">
            <span style="color: {s["color"]}; font-weight: 500;">{message}</span>
        </div>
    '''
