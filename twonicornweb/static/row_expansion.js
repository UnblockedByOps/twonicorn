     $(document).ready(function(){
      var i=1;
     $("#add_row").click(function(){
      $('#addr'+i).html('</td> <td> <span for="artifact_type'+i+'">Artifact Type:</span><br> <select id="artifact_type'+i+'" name="artifact_type" placeholder="Select Something" required> </select> <span class="form_hint">Artifact type</span> </td> <td> <span for="deploy_path'+i+'">Deploy Path:</span><br> <input type="text" id="deploy_path'+i+'" name="deploy_path" placeholder="/app/tomcat/conf" required/> <span class="form_hint">Where this deploy gets installed</span> </td> <td> <span for="package_name'+i+'">Package Name:</span><br> <input type="text" id="package_name'+i+'" name="package_name" placeholder="MyPythonPackage"/> <span class="form_hint">Required for deploys that are deployed using a native package management tool (python (pip), rpm (yum), etc.)</span> </td>');
     $('#artifact_type0 option').clone().appendTo('#artifact_type'+i+'');

      $('#tab_deploy').append('<tr id="addr'+(i+1)+'"></tr>');
      i++;
  });
     $("#delete_row").click(function(){
      if(i>1){
   $("#addr"+(i-1)).html('');
   i--;
   }
  });

});
