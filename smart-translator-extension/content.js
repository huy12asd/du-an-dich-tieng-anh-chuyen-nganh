(async () => {
  const text = document.body.innerText;

  const response = await fetch("https://du-an-dich-tieng-anh-chuyen-nganh-6.onrender.com/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });

  const data = await response.json();
  document.body.innerHTML = data.translated_text;
})();
