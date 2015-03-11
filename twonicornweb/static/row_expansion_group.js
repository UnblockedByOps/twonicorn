/*
   Copyright 2015 CityGrid Media, LLC

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
$(document).ready(function(){
   var i=1;

   $("#add_row").click(function(){
      $('#addr'+i).html('<td> <span for="group_name">Group Name:</span><br> <input type="text" id="group_name" name="group_name" required/> <span class="form_hint">The full AD name of the group</span> </td> <td> <span for="group_perms'+i+'">Promote to prd:</span><br> <input type="checkbox" name="group_perms'+i+'" value="promote_prd"> </td> </td> <td> <span for="group_perms'+i+'">Control Panel:</span><br> <input type="checkbox" name="group_perms'+i+'" value="cp"> </td>');

      $('#tab_group').append('<tr id="addr'+(i+1)+'"></tr>');
      i++;
      $('#delete_row').removeClass( 'disable' );
   });

   $("#delete_row").click(function(){
      if(i>1){
         $("#addr"+(i-1)).html('');
         i--;
         if(i==1){
            $('#delete_row').addClass( 'disable' );
         }
      }

   });

});
