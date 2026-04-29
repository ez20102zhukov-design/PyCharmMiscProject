(function () {
  function getCsrfToken() {
    var csrfInput = document.querySelector(
      'input[name="csrfmiddlewaretoken"]'
    );
    return csrfInput ? csrfInput.value : "";
  }

  function processValueOnBackend(url, inputValue, objectid, onSuccess) {
    if (typeof objectid === "function") {
      onSuccess = objectid;
      objectid = null;
    }

    var params = {source_value: inputValue};
    if (objectid) {
      params.object_id = objectid;
    }
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": getCsrfToken(),
      },
      body: new URLSearchParams(params),
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        if (data && data.fields && typeof onSuccess === "function") {
          onSuccess(data.fields);
          console.log(data.fields);
        }
      })
      .catch(function (error) {
        console.error("Game admin process error:", error);
      });
  }

  function applyFieldsToForm(fields) {
    var generatedImageInput = document.getElementById("id_generated_image_url");
    Object.keys(fields).forEach(function (fieldName) {
      var input = document.getElementById("id_" + fieldName);
      if (!input) {
        return;
      }
      if (input.type === "file") {
        var imageUrl = fields[fieldName];
        showImagePreview(input, imageUrl);
        if (generatedImageInput) {
          generatedImageInput.value = imageUrl || "";
        }
        return;
      }
      input.value = fields[fieldName];
      console.log(input.value);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  function showImagePreview(fileInput, imageUrl) {
    if (!imageUrl || typeof imageUrl !== "string") {
      return;
    }

    var previewWrapId = fileInput.id + "-generated-preview-wrap";
    var previewImageId = fileInput.id + "-generated-preview";
    var wrap = document.getElementById(previewWrapId);
    var image = document.getElementById(previewImageId);

    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = previewWrapId;
      wrap.style.marginTop = "8px";

      var label = document.createElement("div");
      label.textContent = "Generated preview:";
      label.style.fontSize = "12px";
      label.style.color = "#666";
      label.style.marginBottom = "4px";
      wrap.appendChild(label);

      image = document.createElement("img");
      image.id = previewImageId;
      image.alt = "Generated image preview";
      image.style.maxWidth = "240px";
      image.style.height = "auto";
      image.style.display = "block";
      image.style.border = "1px solid #ddd";
      image.style.borderRadius = "4px";
      wrap.appendChild(image);

      fileInput.insertAdjacentElement("afterend", wrap);
    }

    if (!image) {
      return;
    }

    image.src = imageUrl;
    wrap.style.display = "block";
  }
  document.addEventListener("DOMContentLoaded", function () {
    var sourceInput = document.getElementById("id_generated_source");
    var applyButton = document.getElementById("apply-generated-value");

    if (!sourceInput || !applyButton) {
      return;
    }

    var processUrl = sourceInput.dataset.processUrl || "";
    if (!processUrl) {
      return;
    }

    applyButton.addEventListener("click", function () {
      processValueOnBackend(processUrl, sourceInput.value || "", function (fields) {
        applyFieldsToForm(fields);
      });
    });
  });
})();
