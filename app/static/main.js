(function () {

  'use strict';

  angular.module('analyseImageApp', [])

  .controller('analyseImageController', ['$scope', '$log', '$http','$timeout',
    function($scope, $log, $http, $timeout) {
  
    $scope.getResults = function(imageurl) {
  
      // get the URL from the input
      //var imageurl = $scope.imageurl;
      $log.log("Analysing image in the background: "+imageurl);
      //hide HTML bits that don't have data yet
      $scope.waiting = true
  
      // fire the API request
      $http.post('/startimageanalysis', {"imageurl": imageurl}).
        success(function(results) {
          $log.log(results);
          getImageAnalysis(results)
        }).
        error(function(error) {
          $log.log(error);
        });
  
    };
    
    function getImageAnalysis(jobID){
      var timeout = "";

      var poller = function() {
        // fire another request
        $http.get('/results/'+jobID).
          success(function(data, status, headers, config) {
            if(status === 202) {
              $log.log(data, status);
            } else if (status === 200){
              $log.log(data);
              
              $scope.imagecomment = data["imagecomment"]
              $scope.maincolorstrings = data["maincolorstrings"],
              $scope.score = data["score"],
              $scope.colorboxes = data["colorboxes"],
              $scope.simplerimage = data["simplerimage"],
              //unhide HTML bit now that we have data
              $scope.waiting = false
              
              $timeout.cancel(timeout);
              return false;
            }
            // continue to call the poller() function every 2 seconds
            // until the timeout is cancelled
            timeout = $timeout(poller, 2000);
          });
      };
      poller();
    }
    
  
  
  }
  
  
  ]);

}());