"use client";

import { useState } from "react";
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
});

export default function Page() {
  const [reply, setReply] = useState("");

  async function send(formData: FormData) {
    const resp = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: String(formData.get("message")) }],
    });
    setReply(resp.choices[0].message.content ?? "");
  }

  return (
    <form action={send}>
      <input name="message" />
      <button type="submit">Send</button>
      <p>{reply}</p>
    </form>
  );
}
