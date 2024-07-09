async function fetchPositionalData(fileName) {
    try {
        
     
        const fullFileName = $SCRIPT_ROOT + '/api/position_data/' + fileName ;
        const response = await fetch(fullFileName);
        const text = await response.text();

        // Split the text into individual JSON objects (lines)
        const lines = text.trim().split("\n");

        const popup_content_positional_data= document.getElementById("popup-content-positional_data");
        // popup_content_positional_data.textContent = lines;

        // Create a scrollable container for the log entries
    const scrollableDiv = document.createElement('div');
    scrollableDiv.style.overflowY = 'scroll';
    scrollableDiv.style.height = '600px';

    popup_content_positional_data.appendChild(scrollableDiv);

        lines.forEach(entry => {
        const logDiv = document.createElement('div');
        logDiv.textContent = entry; // Set the text content of the div to the log entry
        scrollableDiv.appendChild(logDiv); // Append the div to the container
    });
    

      } catch (error) {
        console.error("Error fetching historic data:", error);
      }


   }

async function showPopup_positionalData(file) {

    //stopLoop = false;
    fetchPositionalData(file)
    showElement_positionalData('popup_positional_data');
    }


async function hidePopup_positionalData() {
  hideElement_positionalData('popup_positional_data');
    }

async function showElement_positionalData(id) {
    var element = document.getElementById(id);
    element.style.display = 'block';
    }

async function hideElement_positionalData(id) {
    var element = document.getElementById(id);

    element.style.display = 'none';
    element.innerHTML = ' <div id="popup-content-positional_data"> </div> <button onclick="hidePopup_positionalData()">Close</button> ' ;
    //stopLoop = true;
  }