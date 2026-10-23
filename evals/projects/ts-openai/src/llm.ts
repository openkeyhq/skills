import OpenAI from "openai";

const client = new OpenAI();

export async function ask(question: string): Promise<string> {
  const resp = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: question }],
  });
  return resp.choices[0].message.content ?? "";
}
