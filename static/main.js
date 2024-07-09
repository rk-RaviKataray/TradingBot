var intervalID = setInterval(update_values, 1000);

async function update_values() {
    $.getJSON($SCRIPT_ROOT + '/get_frontend_data',
        function (data) {
            $('#summary').html(data['html']['summary_html']);
            $('#result').html(data['html']['individual_html']);
        });

    displayISTTime();
};

function stopTextColor() {
    clearInterval(intervalID);
}

// Other functions...

function displayISTTime() {
    

    const ISTOffset = 4.5 * 60 * 60 * 1000; // IST offset in milliseconds (5 hours 30 minutes)
    const now = new Date();
    const ISTTime = new Date(now.getTime() + ISTOffset);

    const hours = ISTTime.getHours().toString().padStart(2, '0');
    const minutes = ISTTime.getMinutes().toString().padStart(2, '0');
    const seconds = ISTTime.getSeconds().toString().padStart(2, '0');

    const timeString = `${hours}:${minutes}:${seconds}`;
    document.getElementById('time').innerText = timeString;
}