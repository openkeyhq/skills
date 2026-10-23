import litellm


def answer(question: str) -> str:
    resp = litellm.completion(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    print(answer("What is a good name for a weather bot?"))
