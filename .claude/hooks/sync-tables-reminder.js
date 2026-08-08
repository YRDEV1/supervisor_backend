let data = "";
process.stdin.on("data", (chunk) => (data += chunk));
process.stdin.on("end", () => {
  try {
    const input = JSON.parse(data);
    const filePath = (
      (input.tool_input && input.tool_input.file_path) ||
      (input.tool_response && input.tool_response.filePath) ||
      ""
    ).replace(/\\/g, "/");

    if (/DATA\/QUERY\.md$/.test(filePath)) {
      console.log(
        JSON.stringify({
          hookSpecificOutput: {
            hookEventName: "PostToolUse",
            additionalContext:
              "DATA/QUERY.md was just created or edited. Check it for any newly-added database table references (e.g. _reference*, _inforg*, _document* tables) and add or update the corresponding entry in DATA/TABLES.md so it stays in sync.",
          },
        })
      );
      return;
    }
  } catch (e) {
    // fall through to no-op
  }
  console.log("{}");
});
