def extract_text(message) -> str:
    content = message.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "text"
            ):
                text = block.get("text")

                if text:
                    text_parts.append(text)

        return "\n".join(text_parts)

    return str(content)


def extract_tool_calls(messages) -> list[dict]:
    calls = []

    for message in messages:
        tool_calls = getattr(
            message,
            "tool_calls",
            None
        )

        if not tool_calls:
            continue

        for call in tool_calls:
            print(f"[TOOL] {call['name']}" )
            print( f"[ARGS] {call['args']}")
            calls.append(
                {
                    "name": call["name"],
                    "args": call.get("args", {})
                }
            )


    return calls