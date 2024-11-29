function search() {
    // Declare variables
    var input, filter, ul, li, a, i, txtValue;
    var count = 0;
    var count_display;
    input = document.getElementById('search_box');
    filter = input.value.toUpperCase();
    ul = document.getElementById("song_list");
    li = ul.getElementsByTagName('li');
    count_display = document.getElementById("songs_found");

    // Loop through all list items, and hide those who don't match the search query
    for (i = 0; i < li.length; i++) {
        a = li[i].getElementsByTagName("a")[0];
        txtValue = a.textContent || a.innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            li[i].style.display = "";
            count += 1;
        } else {
            li[i].style.display = "none";
        }
    }
    count_display.innerText = count;
}