jQuery(document).ready(function(){
    jQuery('.datetimepicker').datepicker({
        timepicker: true,
        language: 'en',
        range: true,
        multipleDates: true,
            multipleDatesSeparator: " - "
      });
    jQuery("#add-event").submit(function(){
        alert("Submitted");
        var values = {};
        $.each($('#add-event').serializeArray(), function(i, field) {
            values[field.name] = field.value;
        });
        console.log(
          values
        );
    });
  });
  
  (function () {    
      'use strict';
      // ------------------------------------------------------- //
      // Calendar
      // ------------------------------------------------------ //
      jQuery(function() {
          // page is ready
          jQuery('#calendar').fullCalendar({
              themeSystem: 'bootstrap4',
              // emphasizes business hours
              businessHours: false,
              defaultView: 'month',
              // event dragging & resizing
              editable: false,
              // header
              header: {
                  left: 'title',
                  center: '',
                  right: 'today prev,next'
              },
              events: events,
              eventRender: function(event, element) {
                  if(event.icon){
                      element.find(".fc-title").prepend("<i class='fa fa-"+event.icon+"'></i>");
                  }
                },
            //   dayClick: function() {
            //       jQuery('#modal-view-event-add').modal();
            //   },
              eventClick: function(event, jsEvent, view) {
                      jQuery('.event-icon').html("<i class='fa fa-"+event.icon+"'></i>");
                      jQuery('.event-title').html(event.title);
                      jQuery('.event-body').html(event.description);
                      if(event.url && event.url.trim() !== '') {
                          jQuery('.eventUrl').attr('href',event.url).show();
                      } else {
                          jQuery('.eventUrl').hide();
                      }
                      jQuery('#modal-view-event').modal();
              },
          })
      });
    
  })(jQuery);