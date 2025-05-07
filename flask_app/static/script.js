let uploaded = false; 
    let chatStateInitialized = false;
    function scrollChat() {
        const messages = document.getElementById("messages");
        messages.scrollTop = messages.scrollHeight;
    }

    document.getElementById('arxiv_subject').addEventListener('change', async function () {
        const subject = this.value;
        const subtopicSelect = document.getElementById('arxiv_subtopic');

        if (subject) {
            try {
                const response = await fetch('/get_subtopics', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({subject: subject}),
                });

                const subtopics = await response.json();

                subtopicSelect.innerHTML = '<option value="">All Subtopics</option>';
                subtopics.forEach(subtopic => {
                    const option = document.createElement('option');
                    option.value = subtopic;
                    option.textContent = subtopic;
                    subtopicSelect.appendChild(option);
                });

                subtopicSelect.disabled = false;
            } catch (error) {
                console.error('Error:', error);
            }
        } else {
            subtopicSelect.innerHTML = '<option value="">Select Subject First</option>';
            subtopicSelect.disabled = true;
        }
    });

    document.getElementById("set-config").addEventListener("click", function () {
        const topics = document.getElementById("topics").value.split(",").map(t => t.trim()).filter(t => t !== "");
        const use_wikipedia = document.getElementById("use_wikipedia").checked;
        const fetch_most_relevant = document.getElementById("fetch_most_relevant").checked;
        const fetch_most_recent = document.getElementById("fetch_most_recent").checked;
        const arxiv_subject = document.getElementById("arxiv_subject").value.trim();
        const arxiv_subtopic = document.getElementById("arxiv_subtopic").value.trim();
        const files = document.getElementById("file-upload").files;
    
        if (topics.length === 0) {
            alert("Please enter at least one topic.");
            return;
        }

        fetch("/init", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({topics, use_wikipedia, fetch_most_relevant, fetch_most_recent, arxiv_subject, arxiv_subtopic, uploaded})
        }).then(response => response.json())
          .then(data => {
              if (data.success) {
                  chatStateInitialized = true;
                  document.getElementById("messages").innerHTML = "";
                  appendMessage("system", `Configuration set: Topics: <strong>${topics.join(", ")}</strong>`);
              }
          });
    });

    function appendMessage(sender, html) {
        const messages = document.getElementById("messages");
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", sender);
        msgDiv.innerHTML = html;
        messages.appendChild(msgDiv);
        scrollChat();
        return msgDiv;
    }

    document.getElementById("chat-form").addEventListener("submit", function (e) {
        e.preventDefault();
        if (!chatStateInitialized) {
            alert("Please set the configuration first.");
            return;
        }

        const promptInput = document.getElementById("prompt");
        const prompt = promptInput.value.trim();
        if (!prompt) return;
        appendMessage("user", `<strong>User:</strong> ${prompt}`);
        promptInput.value = "";

        const assistantMsg = appendMessage("assistant",
            `<strong>Assistant:</strong>
             <div class="assistant-status" style="color: gray;"></div>
             <div class="response-content"></div>
             <div class="citations"></div>`);

        const eventSource = new EventSource("/chat?prompt=" + encodeURIComponent(prompt));

        eventSource.addEventListener("status", function (event) {
            const statusEl = assistantMsg.querySelector(".assistant-status");
            if (statusEl) {
                statusEl.innerHTML = event.data;
                scrollChat();
            }
        });

        eventSource.addEventListener("clearStatus", function () {
            const statusEl = assistantMsg.querySelector(".assistant-status");
            if (statusEl) statusEl.innerHTML = "";
        });

        eventSource.onmessage = function (event) {
            const responseContent = assistantMsg.querySelector(".response-content");
            responseContent.innerHTML += event.data;
            scrollChat();
        };

        eventSource.addEventListener("citation", function (event) {
            const citationsDiv = assistantMsg.querySelector(".citations");
            const citationElem = document.createElement("div");
            citationElem.classList.add("citation");
            citationElem.innerHTML = event.data;
            citationsDiv.appendChild(citationElem);
            scrollChat();
        });

        eventSource.onerror = function () {
            eventSource.close();
        };

        eventSource.addEventListener("end", function () {
            eventSource.close();
        });
    });

    document.getElementById("upload-files").addEventListener("click", function() {
    const files = document.getElementById("file-upload").files;
    if (files.length === 0) {
        alert("Please select files to upload.");
        return;
    }
    else {
        uploaded = true;
    }
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }
    
    const uploadStatus = document.getElementById("upload-status");
    uploadStatus.textContent = "Uploading files...";
    
    fetch("/upload_files", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            uploadStatus.textContent = `Successfully uploaded and processed ${data.file_count} files.`;
            uploaded = true;
            
            // Display uploaded files
            const uploadedFiles = document.getElementById("uploaded-files");
            uploadedFiles.innerHTML = "<p><strong>Uploaded files:</strong></p>";
            const fileList = document.createElement("ul");
            data.files.forEach(file => {
                const item = document.createElement("li");
                item.textContent = file;
                fileList.appendChild(item);
            });
            uploadedFiles.appendChild(fileList);
            
            // Clear the file input
            document.getElementById("file-upload").value = "";
        } else {
            uploadStatus.textContent = `Error: ${data.error}`;
        }
    })
    .catch(error => {
        uploadStatus.textContent = `Upload failed: ${error}`;
    });
});

document.getElementById("reset-btn").addEventListener("click", function() {
  if (!confirm("Are you sure you want to reset the session?")) return;
  fetch("/shutdown", { method: "POST" })
    .then(res => {
      if (!res.ok) throw new Error("Shutdown failed");
      return res.text();
    })
    .then(msg => {
      console.log(msg);
      // reset the frontend state
      chatStateInitialized = false;
      document.getElementById("messages").innerHTML = "";
      document.getElementById("topics").value = "";
      document.getElementById("use_wikipedia").checked = true;
      document.getElementById("fetch_most_relevant").checked = true;
      document.getElementById("fetch_most_recent").checked = false;
      document.getElementById("arxiv_subject").value = "";
      document.getElementById("arxiv_subtopic").innerHTML = '<option value="">Select Subject First</option>';
      document.getElementById("arxiv_subtopic").disabled = true;
      document.getElementById("uploaded-files").innerHTML = "";

      alert("Session has been reset to defaults.");
    })
    .catch(err => {
      console.error(err);
      alert("Failed to reset session: " + err.message);
    });
});
