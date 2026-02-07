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

  function localizeTimestamps() {
    const nodes = document.querySelectorAll(".js-localize-timestamp");
    if (!nodes.length) return;

    nodes.forEach((node) => {
      const iso = node.getAttribute("data-iso");
      if (!iso) return;
      const date = new Date(iso);
      if (Number.isNaN(date.getTime())) return;

      const parts = new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      }).formatToParts(date);

      const part = (type) => parts.find((p) => p.type === type)?.value || "";
      const formatted = `${part("year")}-${part("month")}-${part("day")} ${part(
        "hour"
      )}:${part("minute")}:${part("second")} ${part("dayPeriod")}`;

      node.textContent = formatted.trim();
    });
  }

  function initRuleToggles() {
    const buttons = document.querySelectorAll(".rule-summary");
    if (!buttons.length) return;

    buttons.forEach((btn) => {
      if (btn.dataset.ruleToggleInit === "1") return;
      btn.dataset.ruleToggleInit = "1";

      btn.addEventListener("click", () => {
        const list = btn.parentElement?.querySelector(".rule-list");
        if (!list) return;

        const expanded = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", String(!expanded));
        btn.classList.toggle("is-expanded", !expanded);
        list.classList.toggle("is-hidden", expanded);
      });
    });
  }

  function initHelpPanel() {
    const button = document.getElementById("helpButton");
    const panel = document.getElementById("helpPanel");
    if (!button || !panel) return;

    if (button.dataset.helpInit === "1") return;
    button.dataset.helpInit = "1";

    const closeBtn = panel.querySelector(".help-close");

    function setOpen(isOpen) {
      panel.classList.toggle("active", isOpen);
      panel.setAttribute("aria-hidden", String(!isOpen));
      button.setAttribute("aria-expanded", String(isOpen));
    }

    button.addEventListener("click", () => {
      const isOpen = panel.classList.contains("active");
      setOpen(!isOpen);
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", () => setOpen(false));
    }

    const accordions = panel.querySelectorAll(".help-accordion");
    accordions.forEach((details) => {
      details.addEventListener("toggle", () => {
        if (!details.open) return;
        accordions.forEach((other) => {
          if (other !== details) other.open = false;
        });
      });
    });
  }

  function initFilterDropdowns() {
    const dropdowns = document.querySelectorAll("[data-dropdown]");
    if (!dropdowns.length) return;

    dropdowns.forEach((dropdown) => {
      const toggle = dropdown.querySelector("[data-dropdown-toggle]");
      const menu = dropdown.querySelector("[data-dropdown-menu]");
      if (!toggle || !menu) return;

      if (toggle.dataset.dropdownInit === "1") return;
      toggle.dataset.dropdownInit = "1";

      const selectAll = dropdown.querySelector("[data-select-all]");
      const selectNone = dropdown.querySelector("[data-select-none]");
      const applyBtn = dropdown.querySelector("[data-apply-filter]");

      toggle.addEventListener("click", () => {
        const isOpen = dropdown.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(isOpen));
        if (isOpen) {
          const first = dropdown.querySelector("input[type='checkbox']");
          if (first) first.focus();
        }
      });

      if (selectAll) {
        selectAll.addEventListener("click", () => {
          const boxes = dropdown.querySelectorAll("input[type='checkbox']");
          boxes.forEach((box) => (box.checked = true));
        });
      }

      if (selectNone) {
        selectNone.addEventListener("click", () => {
          const boxes = dropdown.querySelectorAll("input[type='checkbox']");
          boxes.forEach((box) => (box.checked = false));
        });
      }

      if (applyBtn) {
        applyBtn.addEventListener("click", () => {
          const results = document.getElementById("results");
          const runId = results?.dataset?.runId;
          if (!runId || !window.htmx) return;

          const expanded = Array.from(
            results.querySelectorAll(".rule-summary[aria-expanded='true'][data-rule-id]")
          ).map((btn) => btn.dataset.ruleId);

          const selected = Array.from(
            dropdown.querySelectorAll("input[type='checkbox']:checked")
          ).map((box) => box.value);

          let url = `/partials/results?run_id=${encodeURIComponent(runId)}`;
          expanded.forEach((ruleId) => {
            url += `&expanded=${encodeURIComponent(ruleId)}`;
          });
          if (selected.length === 0) {
            url += "&members=__none__";
          } else {
            selected.forEach((name) => {
              url += `&members=${encodeURIComponent(name)}`;
            });
          }

          dropdown.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
          if (applyBtn) {
            applyBtn.setAttribute("data-loading-text", "Applying filter…");
          }
          window.htmx.ajax("GET", url, { target: "#content", swap: "innerHTML" });
        });
      }

      document.addEventListener("click", (event) => {
        if (!dropdown.contains(event.target)) {
          dropdown.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
        }
      });

      dropdown.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          dropdown.classList.remove("is-open");
          toggle.setAttribute("aria-expanded", "false");
          toggle.focus();
        }
      });
    });
  }

  function initDropZone() {
    const dropZone = getDropZone();
    const fileInput = getFileInput();
    if (!dropZone || !fileInput) return;

    if (dropZone.dataset.dropzoneInit === "1") return;
    dropZone.dataset.dropzoneInit = "1";

    const promptEls = [
      dropZone.querySelector(".upload-icon"),
      dropZone.querySelector(".upload-text"),
      dropZone.querySelector(".upload-subtext"),
    ].filter(Boolean);

    function hidePrompt() {
      promptEls.forEach((el) => el.classList.add("is-hidden"));
    }

    function showPrompt() {
      promptEls.forEach((el) => el.classList.remove("is-hidden"));
    }

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
      showPrompt();
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
    dropZone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInput.click();
      }
    });

    fileInput.addEventListener("change", () => {
      clearError();

      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        clearFileUI();
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add("is-hidden");
        }
        return;
      }

      if (!isJsonFile(file)) {
        setError("Invalid file type. Please upload a Trello JSON export.");
        fileInput.value = "";
        clearFileUI();
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add("is-hidden");
        }
        return;
      }

      updateFileUI(file);
      hidePrompt();
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.classList.remove("is-hidden");
      }

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
      submitBtn.disabled = true;
      submitBtn.classList.add("is-hidden");

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
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.classList.add("is-hidden");
        }
        return;
      }

      setFileToInput(file);
      updateFileUI(file);
      hidePrompt();
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.classList.remove("is-hidden");
      }

      if (AUTO_SUBMIT_ON_SELECT) {
        const form = getForm();
        if (form) form.requestSubmit();
      }
    });
  }

  function initLoadingIndicator() {
    const indicator = document.getElementById("loadingIndicator");
    const loadingText = document.getElementById("loadingText");
    if (!indicator) return;
    indicator.classList.remove("active");

    document.body.addEventListener("htmx:beforeRequest", (evt) => {
      if (loadingText) {
        const source = evt.detail.elt;
        const form = source?.closest?.("form");
        const text =
          source?.getAttribute?.("data-loading-text") ||
          form?.getAttribute?.("data-loading-text") ||
          "Working…";
        loadingText.textContent = text;
      }
      indicator.classList.add("active");
    });
    document.body.addEventListener("htmx:afterSwap", () => {
      indicator.classList.remove("active");
    });
    document.body.addEventListener("htmx:responseError", () => {
      indicator.classList.remove("active");
    });
  }

  initDropZone();
  localizeTimestamps();
  initRuleToggles();
  initHelpPanel();
  initFilterDropdowns();
  initLoadingIndicator();
  document.body.addEventListener("htmx:afterSwap", () => {
    initDropZone();
    localizeTimestamps();
    initRuleToggles();
    initFilterDropdowns();
    initLoadingIndicator();
  });

  // -------------------------
  // HTMX integration niceties
  // -------------------------
  document.body.addEventListener("htmx:beforeRequest", (evt) => {
    const content = document.getElementById("content");
    if (content) content.setAttribute("aria-busy", "true");
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
    const content = document.getElementById("content");
    if (content) content.setAttribute("aria-busy", "false");
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
