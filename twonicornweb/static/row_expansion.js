$(document).ready(function(){
      var i=1;
     $("#add_row").click(function(){
      $('#addr'+i).html("<li><input name='name"+i+"' type='text' placeholder='Name' /></li>");

      $('#ul_logic').append('<li id="addr'+(i+1)+'">what the heck</li>');
      i++; 
  });
     $("#delete_row").click(function(){
         if(i>1){
         $("#addr"+(i-1)).html('');
         i--;
         }
     });

});
