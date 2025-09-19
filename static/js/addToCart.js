$(document).on("click", ".add-to-cart", function(e){
    e.preventDefault();
    let card = $(this).closest(".col-6, .col-md-4, .col-lg-3");
    let variantId = card.find(".size-select").val();

    if(!variantId){
        alert("Please select a size before adding to cart.");
        return;
    }

    $.ajax({
        url: "/wishlist/add-to-cart/" + variantId + "/",  // ✅ trailing slash
        type: "POST",
        headers: {"X-CSRFToken": "{{ csrf_token }}"},
        success: function(res){
            if(res.status === "success"){
                alert(res.message);  // stay on same page
                card.fadeOut();      // optional
            } else {
                alert(res.message);
            }
        },
        error: function(xhr){
            console.error(xhr.responseText);
            alert("Something went wrong");
        }
    });
});

$(document).on("click", ".remove-wishlist", function(e){
    e.preventDefault();
    let itemId = $(this).data("id");
    let card = $(this).closest(".col-6, .col-md-4, .col-lg-3");

    $.ajax({
        url: "/wishlist/remove/" + itemId + "/", // ✅ trailing slash
        type: "POST",
        headers: {"X-CSRFToken": "{{ csrf_token }}"},
        success: function(res){
            if(res.status === "success"){
                card.fadeOut();
                alert("Removed from wishlist");
            }
        },
        error: function(xhr){
            console.error(xhr.responseText);
            alert("Error removing from wishlist");
        }
    });
});
