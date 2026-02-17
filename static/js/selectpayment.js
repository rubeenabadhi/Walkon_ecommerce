    
    // Helper functions
    function resetButton() {
        const btn = $("#continueToShipping");
        btn.prop("disabled", false);
        btn.html('Continue to Shipping');
    }

    // CSRF via cookie (standard Django)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // Coupon apply/remove (your existing code - unchanged, good)
    $(document).on("submit", "#applyCouponForm, #removeCouponForm", function(e) {
        e.preventDefault();
        const form = $(this);
        const url = form.attr("action");
        const data = form.serialize();

        $.ajax({
            url: url,
            type: "POST",
            data: data,
            success: function(response) {
                if (response.status === "success") {
                    $("#final_total").val(response.final_total);
                    $("#final_total_display").text(`₹${response.final_total}`);

                    if (response.applied_coupon) {
                        $("#coupon-section").html(`
                            <div class="alert alert-success p-2 mt-2">
                                Coupon <strong>"${response.applied_coupon.code}"</strong> applied
                                <span class="float-end">-₹${response.discount}</span>
                            </div>
                            <form method="post" action="${removeCouponUrl}" id="removeCouponForm">
                                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                                <button type="submit" class="btn btn-sm btn-danger w-100 mt-2">Remove Coupon</button>
                            </form>
                        `);
                    } else {
                        $("#coupon-section").html(`
                            <form method="post" action="{% url 'apply_coupon' %}" id="applyCouponForm" class="d-flex gap-2 mt-3">
                                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                                <input type="text" name="coupon_code" placeholder="Enter coupon code" class="form-control" required>
                                <button type="submit" class="btn btn-sm btn-dark">Apply</button>
                            </form>
                        `);
                    }
                    location.reload();
                } else {
                    alert(response.message || "Failed to apply coupon.");
                }
            },
            error: function(xhr, status, error) {
                console.error("Coupon AJAX error:", error);
                alert("Something went wrong with coupon. Try again.");
            }
        });
    });

    // Payment form submission - MAIN FIX HERE
    $("#payment-form").on("submit", function(e) {
        e.preventDefault();  // Block all default submits initially

        const btn = $("#continueToShipping");

        // Prevent duplicate submission
        if (btn.prop("disabled")) {
            console.log("Already submitting - ignoring duplicate click");
            return false;
        }

        // Disable button & show loading
        btn.prop("disabled", true);
        btn.html('<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing...');

        const selectedMethod = document.querySelector("input[name='payment_method']:checked");

        if (!selectedMethod) {
            alert("Please select a payment method.");
            resetButton();
            return;
        }

        const method = selectedMethod.value;
        const order_id = document.getElementById("order_id")?.value;
        const final_total = document.getElementById("final_total")?.value;

        if (method === "razorpay") {
            // Razorpay payment flow
            fetch(`/checkout/create-razorpay-order/${order_id}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken
                },
                body: JSON.stringify({ amount: final_total })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    resetButton();
                    return;
                }

                let options = {
                    "key": data.razorpay_key,

                    "currency": data.currency,
                    "name": "WalkOn",
                    "description": "Order Payment",
                    "order_id": data.razorpay_order_id,
                    "handler": function(response) {
                        fetch("/checkout/verify-razorpay-payment/", {
                            method: "POST",
                            headers: {
                                "X-CSRFToken": csrftoken,
                                "Content-Type": "application/x-www-form-urlencoded"
                            },
                            body: new URLSearchParams(response)
                        })
                        .then(res => res.json())
                        .then(resData => {
                            if (resData.status === "success") {
                                window.location.href = `/checkout/order-success/${resData.order_id}/`;
                            } else {
                                alert(resData.message || "Payment verification failed.");
                                window.location.href = "/checkout/payment-failed/";
                            }
                        })
                        .catch(err => {
                            console.error("Verification error:", err);
                            alert("Payment verification failed.");
                            window.location.href = "/checkout/payment-failed/";
                        });
                    },
                    "theme": {"color": "#3399cc"},
                    "modal": {
                        "ondismiss": function() {
                            alert("Payment was cancelled.");
                            resetButton();
                            // Optional: save failure
                            fetch(`/checkout/payment-failure-save/${order_id}/`, {
                                method: "POST",
                                headers: { "X-CSRFToken": csrftoken }
                            }).then(() => {
                                window.location.href = "/checkout/payment-failed/";
                            });
                        }
                    }
                };

                let rzp1 = new Razorpay(options);

                rzp1.on("payment.failed", function(response) {
                    alert("Payment failed: " + response.error.description);
                    resetButton();
                    fetch(`/checkout/payment-failure-save/${order_id}/`, {
                        method: "POST",
                        headers: { "X-CSRFToken": csrftoken }
                    }).then(() => {
                        window.location.href = "/checkout/payment-failed/";
                    }).catch(err => {
                        console.error("Failure save error:", err);
                        window.location.href = "/checkout/payment-failed/";
                    });

                });

                rzp1.open();
            })
            .catch(err => {
                console.error("Razorpay create error:", err);
                alert("Failed to initiate Razorpay.");
                resetButton();
            });
        } 
        else if (method === "wallet") {
            fetch(`/checkout/wallet-payment/${order_id}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrftoken
                },
                body: JSON.stringify({ amount: final_total })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === "success") {
                    window.location.href = data.redirect_url;
                } else {
                    alert(data.message || "Wallet payment failed.");
                    window.location.href = "/checkout/payment/";
                }
            })
            .catch(err => {
                console.error("Wallet payment error:", err);
                alert("Wallet payment failed.");
                resetButton();
            });
        } 
        else if (method === "cod") {
            // COD: Submit the form normally (button already disabled)
            console.log("Submitting COD order...");
            this.submit();  // This will redirect to place_order view
            // No resetButton() here - redirect will happen
        }
    });
