console.log("✅ popup.js loaded");

document.addEventListener("DOMContentLoaded", function () {
  const button = document.getElementById("scanBtn");
  const statusEl = document.getElementById("status");
  const resultEl = document.getElementById("result");
  const predictionEl = document.getElementById("prediction");
  const confidenceEl = document.getElementById("confidence");

  button.addEventListener("click", async function () {
    statusEl.textContent = "🔍 Scanning...";

    // Get active tab URL
    chrome.tabs.query({ active: true, currentWindow: true }, async function (tabs) {
      const url = tabs[0].url;

      try {
        const response = await fetch("http://127.0.0.1:5000/predict", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ url }),
        });

        const data = await response.json();

        // ✅ Display result
        statusEl.textContent = "✅ Scan Completed";
        resultEl.classList.remove("hidden");
        predictionEl.textContent = data.prediction;
        confidenceEl.textContent = data.confidence;
      } catch (error) {
        statusEl.textContent = "❌ Server Not Found.";
        console.error("Fetch error:", error);
      }
    });
  });
});
