// walkon_project/static/js/user_js.js
// Function to handle OTP timer and resend button
let timeLeft = 60;
    let timerDisplay = document.getElementById("timer");
    let resendBtn = document.getElementById("resendBtn");

    let countdown = setInterval(function () {
        if (timeLeft <= 0) {
            clearInterval(countdown);
            resendBtn.disabled = false; // Enable button
            resendBtn.classList.remove("btn-secondary");
            resendBtn.classList.add("btn-primary");
        } else {
            timeLeft--;
            let seconds = timeLeft < 10 ? "0" + timeLeft : timeLeft;
            timerDisplay.textContent = "00:" + seconds;
        }
    }, 1000);
