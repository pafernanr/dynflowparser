// expand non success branchs automatically
function expanderrors() {
  $('tr.error, tr.warning, tr.pending, tr.skipped, tr.suspended').each(function(){
    $('#tblAction').treetable('expandNode', 1);
    id = $(this).attr('data-tt-id');
    // $('#details_'+id).show();
    $('#tblAction').treetable('expandNode', id);
    parentid = $(this).attr('data-tt-parent-id');
    while (parentid > 0) {
  	  $('#tblAction').treetable('expandNode', parentid);
  	  parentid = $('tr[data-tt-id="'+parentid+'"]').attr('data-tt-parent-id')
    }
  })
}

$( document ).ready(function() {
	// Create tree
  $("#tblAction").treetable({ 
    expandable: true, 
    initialState: "collapsed",
    onNodeCollapse: function() {
      var rowobject = this.row;
      id = $(rowobject).attr('data-tt-id');
      $('.details').hide();
    }
  });
  // Expand non Success nodes
  expanderrors();
  // set action details indentation
  $('.action td span.show').each(function() {
      tr = $(this).parent().parent()
      id = $(tr).attr("data-tt-id")
      pos = $(this).parent().children(".folder").offset()
      $('#details_'+id).children('td').css('padding-left', pos.left+20+'px')
  });
  // set step details indentation
  $('.step td span.show').each(function() {
      tr = $(this).parent().parent()
      id = $(tr).attr("data-tt-id")
      pos = $(this).parent().children(".file").offset()
      $('#details_'+id).children('td').css('padding-left', pos.left+20+'px')
  });
  // show/hide details action
  $('.show').click(function(){
    tr = $(this).parent().parent();
    id = $(tr).attr("data-tt-id");
    $(".details:not(#details_"+id+")").fadeOut('slow');
    $('#details_'+id).fadeToggle('slow');
  });
  // add tabs show/hide events
  $('.container').fadeOut('slow')
  $('.tabs li a:not(".open")').addClass('inactive');
  $('div.open').fadeIn('slow')
  $('.tabs li a').click(function(){
  	var t = $(this).attr('id');
    if ($(this).hasClass('inactive')){ //this is the start of our condition 
  	    $(this).parent().parent().children('li').children('a').addClass('inactive');           
  	    $(this).removeClass('inactive');
        $(this).parent().parent().children('li').children('.container').hide();
  	    $('#'+ t + '_c').fadeIn('slow');
    }
  });

});