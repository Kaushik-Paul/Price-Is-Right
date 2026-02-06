# Foreground colors
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'

# Background color
BG_BLACK = '\033[40m'
BG_BLUE = '\033[44m'

# Reset code to return to default color
RESET = '\033[0m'

mapper = {
    BG_BLACK+RED: "#ff6b6b",      # Bright coral red
    BG_BLACK+GREEN: "#4ade80",     # Bright green
    BG_BLACK+YELLOW: "#ffd700",    # Gold - more readable than dark yellow
    BG_BLACK+BLUE: "#5dade2",      # Bright sky blue - more readable than dark blue
    BG_BLACK+MAGENTA: "#da70d6",   # Bright orchid - more readable than dark magenta
    BG_BLACK+CYAN: "#22d3ee",      # Bright cyan
    BG_BLACK+WHITE: "#f0f0f0",     # Near white
    BG_BLUE+WHITE: "#ff9f43"       # Bright orange
}


def reformat(message):
    for key, value in mapper.items():
        message = message.replace(key, f'<span style="color: {value}">')
    message = message.replace(RESET, '</span>')
    return message
    
    