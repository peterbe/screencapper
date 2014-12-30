$(function() {
  $('form').on('submit', function() {
    var number = parseInt($('input[name="number"]', this).val());
    if (number <= 0) {
      alert("Too few"); return false;
    } else if (number > 100) {
      alert("Too many"); return false;
    }
    var url = $('input[name="url"]', this).val().trim();
    if (!url.length) {
      return false;
    }
    $.post('/transform', {number: number, url: url})
    .done(function(response) {
      console.log(response);
      $('#duration').text(response.duration);
      $('#download_time').text(response.time.download);
      $('#transform_time').text(response.time.transform);
      $('#total_time').text(response.time.total);
      var _images = $('#images');
      $('img', _images).empty();
      var _p;
      $.each(response.urls, function(i, url) {
        console.log(i, url);
        _p = $('<p>')
        $('<img>').attr('src', url).appendTo(_p);
        $('<br>').appendTo(_p);
        $('<a>').attr('href', url).text(url).appendTo(_p);
        _p.appendTo(_images);
      });
      $('#result').show();
    })
    .error(function() {
      console.error(arguments);
    });
    return false;
  });
});
