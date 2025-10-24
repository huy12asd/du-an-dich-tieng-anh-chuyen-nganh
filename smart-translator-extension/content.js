(async () => {
  const text = document.body.innerText;

  const response = await fetch("http://127.0.0.1:5000/api/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });

  const data = await response.json();
  document.body.innerHTML = data.translated_text;
})();
