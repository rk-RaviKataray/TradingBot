

let stopLoop = false;
async function fetchHistoricData(fileName) {
    async function updateHistoricData(fileName) {
      while(!stopLoop){
        await new Promise(r => setTimeout(r, 62000));
        
        const fullFileName =  $SCRIPT_ROOT + "/api/candle_data/" + fileName ;

        const response = await fetch(fullFileName);
        const text = await response.text();

        // Split the text into individual JSON objects (lines)
        const lines = text.trim().split("\n");
        const lin = lines.slice(-1)[0];

        // Parse each JSON object and create an array of data points
    
        const historicData = JSON.parse(lin);
        const candlestickSeries = chart.addCandlestickSeries();
        
        candlestickSeries.update(historicData);

      }
    }


  const chart = LightweightCharts.createChart(document.getElementById('popup-content'), {
    width: 800,
    height: 600,
    watermark:{
        color: 'rgba(0, 0, 0, 1)', // Watermark text color
        fontSize: 16,                  // Watermark font size
        horzAlign: 'left',           // Horizontal alignment: 'left', 'center', or 'right'
        vertAlign: 'top',           // Vertical alignment: 'top', 'middle', or 'bottom'
        visible: true,                 // Set to false to hide the watermark
        text: fileName,             // Watermark text
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {
        width: 8,
        color: '#C3BCDB44',
        style: LightweightCharts.LineStyle.Solid,
        labelBackgroundColor: '#9B7DFF',
  },

      // Horizontal crosshair line (showing Price in Label)
      horzLine: {
        color: '#9B7DFF',
        labelBackgroundColor: '#9B7DFF',
      },
    },
    timeScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
        timeVisible: true,
        secondsVisible: true,
    },
    
    });


  try {
    
    const myArray = fileName;

    //document.getElementById("chart_name").innerHTML = fileName; 
    // Replace 'historic_data.jsonl' with the path to your JSONL file
    const fullFileName = $SCRIPT_ROOT + "/api/candle_data/" + fileName ;
    const response = await fetch(fullFileName);
    const text = await response.text();

    // Split the text into individual JSON objects (lines)
    const lines = text.trim().split("\n");
    //console.log(lines)

    // Parse each JSON object and create an array of data points
    const historicData = lines.map((line) => JSON.parse(line));
    
    const candlestickSeries = chart.addCandlestickSeries();

    candlestickSeries.setData(historicData);

    updateHistoricData(fileName)


  } catch (error) {
    console.error("Error fetching historic data:", error);
  }


 

}


async function showPopup(file) {

stopLoop = false;
fetchHistoricData(file)
showElement('popup');
}


async function hidePopup() {
hideElement('popup');
}

async function showElement(id) {
var element = document.getElementById(id);
element.style.display = 'block';
}

async function hideElement(id) {
var element = document.getElementById(id);

element.style.display = 'none';
element.innerHTML = ' <div id="popup-content"> </div> <button onclick="hidePopup()">Close</button> ' ;
stopLoop = true;


}