(function () {
  function getCsrfToken() {
    var csrfInput = document.querySelector(
      'input[name="csrfmiddlewaretoken"]'
    );
    return csrfInput ? csrfInput.value : "";
  }

  function processValueOnBackend(url, inputValue, objectid, onSuccess) {
    var params = {source_value: inputValue}
    if (objectid) {
      params.object_id = objectid;
    }
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": getCsrfToken(),
      },
      body: new URLSearchParams({
        params
      }),
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        if (data && data.fields) {
          onSuccess(data.fields);
          console.log(data.fields)
        }
      })
      .catch(function (error) {
        console.error("Game admin process error:", error);
      });
  }

  function applyFieldsToForm(fields) {
    Object.keys(fields).forEach(function (fieldName) {
      var input = document.getElementById("id_" + fieldName);
      if (!input) {
        return;
      }
      if (input.type==="file") {
        return;
      }
      input.value = fields[fieldName];
      console.log(input.value);
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
  function ShowImagePreview (url) {
    var wrap = document.getElementById("game-admin-image-preview-wrap")
    var image = document.getElementById("game-admin-image-preview")
    if (!wrap) {
      
    }
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
