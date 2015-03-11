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
      $('#addr'+i).html('</td> <td> <span for="artifact_type'+i+'">Artifact Type:</span><br> <select id="artifact_type'+i+'" name="artifact_type" placeholder="Select Something" required> </select> <span class="form_hint">Artifact type</span> </td> <td> <span for="deploy_path'+i+'">Deploy Path:</span><br> <input type="text" id="deploy_path'+i+'" name="deploy_path" placeholder="/app/tomcat/conf" required/> <span class="form_hint">Where this deploy gets installed</span> </td> <td> <span for="package_name'+i+'">Package Name:</span><br> <input type="text" id="package_name'+i+'" name="package_name" placeholder="MyPythonPackage"/> <span class="form_hint">Required for deploys that are deployed using a native package management tool (python (pip), rpm (yum), etc.)</span> </td>');

//      $('#artifact_type0:last option').clone().appendTo('#artifact_type'+i+'');
      var choices = $('#artifact_type0:last option').clone()
      choices.removeAttr('selected');
      choices.first().prop( 'selected', true );
      choices.appendTo('#artifact_type'+i+'');

      $('#tab_deploy').append('<tr id="addr'+(i+1)+'"></tr>');
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
