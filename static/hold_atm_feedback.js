
var buttonColor = localStorage.getItem('buttonColor') || 'red';

// Apply the initial color to the button
document.getElementById('hold-atm').style.backgroundColor = buttonColor;

function changeButtonText() {
    // Get the button element
    var button = document.getElementById('hold-atm');

    // Toggle between red and green
    if (buttonColor === 'red') {
    button.style.backgroundColor = 'green';
    buttonColor = 'green';
    } else {
    button.style.backgroundColor = 'red';
    buttonColor = 'red';
    }

    localStorage.setItem('buttonColor', buttonColor);
}

