// src/static/js/app.js
(() => {
  const AUTO_SUBMIT_ON_SELECT = false;

  function getDropZone() {
    return document.getElementById("dropZone");
  }

  function getFileInput() {
    return document.getElementById("fileInput");
  }

  function getErrorMsg() {
    return document.getElementById("errorMsg");
  }

  function setError(message) {
    const errorMsg = getErrorMsg();
    if (!errorMsg) return;
    errorMsg.textContent = message;
    errorMsg.classList.add("active");
  }

  function clearError() {
    const errorMsg = getErrorMsg();
    if (!errorMsg) return;
    errorMsg.textContent = "";
    errorMsg.classList.remove("active");
  }

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const value = bytes / Math.pow(k, i);
    return `${value.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
  }

  function isJsonFile(file) {
    if (!file) return false;
    const nameOk = (file.name || "").toLowerCase().endsWith(".json");
    // Some browsers set type empty; accept if extension looks right.
    const typeOk =
      file.type === "application/json" || file.type === "" || file.type === "text/json";
    return nameOk && typeOk;
  }

  function initDropZone() {
    const dropZone = getDropZone();
    const fileInput = getFileInput();
    if (!dropZone || !fileInput) return;

    if (dropZone.dataset.dropzoneInit === "1") return;
    dropZone.dataset.dropzoneInit = "1";

    // Ensure file info container exists (optional UI)
    let fileInfo = dropZone.querySelector(".file-info");
    if (!fileInfo) {
      fileInfo = document.createElement("div");
      fileInfo.className = "file-info";
      fileInfo.innerHTML = `
        <div class="file-name" id="fileName"></div>
        <div class="file-size" id="fileSize"></div>
      `;
      dropZone.appendChild(fileInfo);
    }

    const fileNameEl = document.getElementById("fileName");
    const fileSizeEl = document.getElementById("fileSize");

    function updateFileUI(file) {
      if (!fileInfo || !fileNameEl || !fileSizeEl) return;

      fileNameEl.textContent = file.name || "(unnamed)";
      fileSizeEl.textContent = formatBytes(file.size || 0);
      fileInfo.classList.add("active");
    }

    function clearFileUI() {
      if (!fileInfo || !fileNameEl || !fileSizeEl) return;

      fileNameEl.textContent = "";
      fileSizeEl.textContent = "";
      fileInfo.classList.remove("active");
    }

    function getForm() {
      // Find the form inside the dropZone label
      return dropZone.querySelector("form");
    }

    function setFileToInput(file) {
      // Programmatically set input files via DataTransfer
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
    }

    // -------------------------
    // Events: file picker select
    // -------------------------
    // Only clicks on the box open the file picker
    dropZone.addEventListener("click", (e) => {
      // Don't trigger when clicking the submit button
      if (e.target.closest("button")) return;
      fileInput.click();
    });

    fileInput.addEventListener("change", () => {
      clearError();

      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        clearFileUI();
        return;
      }

      if (!isJsonFile(file)) {
      setError("Invalid file type. Please upload a Trello JSON export.");
        fileInput.value = "";
        clearFileUI();
        return;
      }

      updateFileUI(file);

      if (AUTO_SUBMIT_ON_SELECT) {
        const form = getForm();
        if (form) form.requestSubmit();
      }
    });

    // -------------------------
    // Drag & drop support
    // -------------------------
    const submitBtn = dropZone.querySelector("button[type='submit']");
    if (submitBtn) {
      // Prevent submit button clicks from being treated as "browse".
      submitBtn.addEventListener("click", (e) => e.stopPropagation());
    }

    ["dragenter", "dragover"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((evt) => {
      dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", (e) => {
      clearError();

      const files = e.dataTransfer?.files;
      if (!files || files.length === 0) return;

      const file = files[0];

      if (!isJsonFile(file)) {
      setError("Invalid file type. Please upload a Trello JSON export.");
        return;
      }

      setFileToInput(file);
      updateFileUI(file);

      if (AUTO_SUBMIT_ON_SELECT) {
        const form = getForm();
        if (form) form.requestSubmit();
      }
    });
  }

  initDropZone();
  document.body.addEventListener("htmx:afterSwap", initDropZone);

  // -------------------------
  // HTMX integration niceties
  // -------------------------
  document.body.addEventListener("htmx:beforeRequest", (evt) => {
    const form = evt.detail.elt?.closest?.("form");
    if (form) {
      const btn = form.querySelector("button[type='submit']");
      if (btn) btn.disabled = true;
    }

    // If the request came from our form, you can optionally show a loading state later
    // (only if you add a .loading element in the partial).
    // Keeping scaffold minimal: just clear error here.
    const dropZone = getDropZone();
    const elt = evt.detail.elt;
    if (dropZone && elt && dropZone.contains(elt)) clearError();
  });

  document.body.addEventListener("htmx:afterRequest", (evt) => {
    const form = evt.detail.elt?.closest?.("form");
    if (!form) return;
    const btn = form.querySelector("button[type='submit']");
    if (btn) btn.disabled = false;
  });

  document.body.addEventListener("htmx:responseError", (evt) => {
    // If server returns 4xx/5xx and doesn't swap an error partial,
    // show a generic message.
    setError("Analyze failed. Please try again or check the server log.");
  });
})();
