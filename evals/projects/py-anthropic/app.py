import anthropic

client = anthropic.Anthropic()


def ask(question: str) -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": question}],
    )
    return msg.content[0].text


if __name__ == "__main__":
    print(ask("Give me three names for a note-taking app."))
