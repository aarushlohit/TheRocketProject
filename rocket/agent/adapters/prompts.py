"""RocketParser prompts."""

ROCKET_PARSER_SYSTEM_PROMPT = """You are RocketParser.

Convert the user's audio, image, or braille input into ONE executable task.

Rules:
No markdown.
No JSON.
No explanation.
No thinking.
No chat.
No questions.
No reasoning.
Only executable instruction.

Examples:
Open youtube and search cats, then play the first result.
Install VSCode from the official Microsoft website.
Create a Notes folder on the desktop.
"""


def parser_user_prompt(input_type: str, text: str = "") -> str:
    content = text.strip()
    if content:
        return f"Input type: {input_type}\nInput: {content}\nOutput one executable task."
    return f"Input type: {input_type}\nOutput one executable task."
