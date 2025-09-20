
console.log("AddToCart.js loaded");


// Add to Cart Handler
$(document).on("click", ".add-to-cart, .add-to-cart-btn", function (e) {
    e.preventDefault();

    let card = $(this).closest(".product-card, .col-6, .col-md-4, .col-lg-3");
    let sizeSelect = card.find(".size-select");
    let variantId = null;

    if (sizeSelect.length > 0) {
        // Wishlist flow: direct dropdown select
        variantId = sizeSelect.val();

        if (!variantId) {
            alert("⚠️ Please select a size before adding to cart.");
            return;
        }

        addToCartAjax(variantId, card);

    } else {
        // Other product pages → open modal
        let productId = $(this).data("product-id");

        // Save product card reference for later use
        $("#sizeModal").data("card", card);

        // Clear & populate modal dropdown
        let sizeDropdown = $("#modalSizeSelect");
        sizeDropdown.empty().append('<option value="">-- Select Size --</option>');

        // ✅ Load product sizes via AJAX
    $.getJSON(`/product/${productId}/sizes/`, function (res) {
        // Use Set to ensure unique sizes
        let seen = new Set();
        res.sizes.forEach(function (variant) {
            if (!seen.has(variant.label)) {
                seen.add(variant.label);
                sizeDropdown.append(
                    `<option value="${variant.id}">Size: ${variant.label}</option>`
                );
            }
        });

    }
        );

        // Show modal
        var modal = new bootstrap.Modal(document.getElementById('sizeModal'));
        modal.show();
    }
});

// Confirm Add to Cart inside modal
$(document).on("click", "#confirmAddToCart", function () {
    let variantId = $("#modalSizeSelect").val();
    let card = $("#sizeModal").data("card");

    if (!variantId) {
        alert("⚠️ Please select a size.");
        return;
    }

    $("#sizeModal").modal("hide");
    addToCartAjax(variantId, card);
});

// ✅ Reusable AJAX Call
function addToCartAjax(variantId, card) {
    $.ajax({
        url: `${addToCartBaseUrl}${variantId}/`, // ✅ works for wishlist & product pages
        type: "POST",
        headers: { "X-CSRFToken": csrfToken },
        success: function (response) {
            if (response.status === "success") {
                alert(`✅ ${response.message}`);
                if (card && card.find(".size-select").length > 0) {
                    // Wishlist → remove product from wishlist card
                    card.fadeOut();
                }
            } else {
                alert(`❌ ${response.message}`);
            }
        },
        error: function (xhr) {
            console.error(xhr.responseText);
            alert("⚠️ Something went wrong while adding to cart.");
        },
    });
}
$(document).on("click", ".remove-wishlist", function(e){
    e.preventDefault();
    let variantId = $(this).data("id");
    let card = $(this).closest(".col-6, .col-md-4, .col-lg-3");

    if (!variantId) {
        alert("❌ Variant ID not found!");
        return;
    }

    $.ajax({
        url: `/wishlist/remove/${variantId}/`,
        type: "POST",
        headers: {"X-CSRFToken": csrfToken}, // make sure csrfToken variable exists
        success: function(res){
            if(res.status === "success"){
                card.fadeOut();
                alert("✅ Removed from wishlist");
            } else {
                alert(`❌ ${res.message || "Error removing from wishlist"}`);
            }
        },
        error: function(xhr){
            console.error(xhr.responseText);
            alert("❌ Error removing from wishlist");
        }
    });
});

