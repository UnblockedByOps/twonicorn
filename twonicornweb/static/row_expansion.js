     $(document).ready(function(){
      var i=1;
//     var content = $('select').html();
     $("#add_row").click(function(){
     // $('#addr'+i).html('<td>'+ content +' </td> <td> <span for="artifact_type'+i+'">Artifact Type:</span><br> <select id="artifact_type'+i+'" name="artifact_type" placeholder="Select Something" required> <option value="" disabled="disabled" selected="selected">Please select an artifact Type</option> <option tal:repeat="item artifact_types" tal:content="item.name"></option> </select> <span class="form_hint">Artifact type</span> </td> <td> <span for="deploy_path'+i+'">Deploy Path:</span><br> <input type="text" id="deploy_path'+i+'" name="deploy_path" placeholder="/app/tomcat/conf" required/> <span class="form_hint">Where this deploy gets installed</span> </td> <td> <span for="package_name'+i+'">Package Name:</span><br> <input type="text" id="package_name'+i+'" name="package_name" placeholder="MyPythonPackage"/> <span class="form_hint">Required for deploys that are deployed using a native package management tool (python (pip), rpm (yum), etc.)</span> </td>');
      $('#addr'+i).html('<td>'+ (i+1) +' </td> <td> <span for="artifact_type'+i+'">Artifact Type:</span><br> <select id="artifact_type'+i+'" name="artifact_type" placeholder="Select Something" required> </select> <span class="form_hint">Artifact type</span> </td> <td> <span for="deploy_path'+i+'">Deploy Path:</span><br> <input type="text" id="deploy_path'+i+'" name="deploy_path" placeholder="/app/tomcat/conf" required/> <span class="form_hint">Where this deploy gets installed</span> </td> <td> <span for="package_name'+i+'">Package Name:</span><br> <input type="text" id="package_name'+i+'" name="package_name" placeholder="MyPythonPackage"/> <span class="form_hint">Required for deploys that are deployed using a native package management tool (python (pip), rpm (yum), etc.)</span> </td>');
     $('#artifact_type0 option').clone().appendTo('#artifact_type'+i+'');

/*
This is what we need to add:

<td>
1
</td>
<td>
  <span for="artifact_type0">Artifact Type:</span><br>
    <select id="artifact_type0" name="artifact_type" placeholder="Select Something" required>
      <option value="" disabled="disabled" selected="selected">Please select an artifact Type</option>
      <option tal:repeat="item artifact_types" tal:content="item.name"></option>
    </select>
  <span class="form_hint">Artifact type</span>
</td>
<td>
  <span for="deploy_path0">Deploy Path:</span><br>
  <input type="text" id="deploy_path0" name="deploy_path" placeholder="/app/tomcat/conf" required/>
  <span class="form_hint">Where this deploy gets installed</span>
</td>
<td>
  <span for="package_name0">Package Name:</span><br>
  <input type="text" id="package_name0" name="package_name" placeholder="MyPythonPackage"/>
  <span class="form_hint">Required for deploys that are deployed using a native package management tool (python (pip), rpm (yum), etc.)</span>
</td>


And this is what it was before I started messing with it:

      $('#addr'+i).html("<td>"+ (i+1) +"</td><td><input name='name"+i+"' type='text' placeholder='Name' class='form-control input-md'  /> </td><td><input  name='mail"+i+"' type='text' placeholder='Mail'  class='form-control input-md'></td><td><input  name='mobile"+i+"' type='text' placeholder='Mobile'  class='form-control input-md'></td>");

*/


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
