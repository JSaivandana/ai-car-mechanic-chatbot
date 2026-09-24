import Head from "next/head";
import ChatWindow from "../components/ChatWindow";

export default function Home() {
  return (
    <>
      <Head>
        <title>AI Car Mechanic Chatbot</title>
        <meta
          name="description"
          content="Chat with a virtual car mechanic for troubleshooting and diagnosis."
        />
      </Head>
      <main>
        <ChatWindow />
      </main>
    </>
  );
}
