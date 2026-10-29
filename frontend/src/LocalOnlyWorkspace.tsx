export default function LocalOnlyWorkspace() {
  return (
    <main style={{ minHeight: "100vh", padding: "8rem 2rem", maxWidth: 720, margin: "0 auto" }}>
      <h1>The investigation workspace runs locally.</h1>
      <p>
        This public deployment serves the read-only National Explorer. Clone the repository and follow the local setup guide
        to import your own measurements, preserve private data, and run the research engine on your computer.
      </p>
      <p><a href="/local">Read the local setup guide</a></p>
      <p><a href="/">Return to the National Explorer</a></p>
    </main>
  );
}
