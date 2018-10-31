var renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

var scene = new THREE.Scene();
var camera = new THREE.PerspectiveCamera(100, window.innerWidth/window.innerHeight, 0.1, 1000);
camera.position.z = 1.5;

window.addEventListener('resize', function (event) {
	renderer.setSize(window.innerWidth, window.innerHeight);
	camera.aspect = window.innerWidth / window.innerHeight;
	camera.updateProjectionMatrix();

});

var light = new THREE.AmbientLight(0xffffff);
scene.add(light);

var sphere_geometry = new THREE.SphereGeometry(1, 32, 32);
var sphere_material = new THREE.MeshPhongMaterial({wireframe: true, color: 0x0000ff,  transparent: true});
var sphere_wire = new THREE.Mesh(sphere_geometry, sphere_material);
sphere_material.opacity = 0.5;
sphere_material.side = THREE.BackSide;
scene.add(sphere_wire);

var sphere_geometry = new THREE.SphereGeometry(1, 32, 32);
var sphere_material = new THREE.MeshPhongMaterial({color: 0x0000ff,  transparent: true});
var sphere = new THREE.Mesh(sphere_geometry, sphere_material);
sphere_material.opacity = 0.5;
sphere_material.side = THREE.BackSide;
scene.add(sphere);

var goal_stars = [];
var majorana_stars = [];
var mixed_stars = [];
var me = 0;
var camera_mode = "sphere";
var changed = false;
var last = "";
var other_selected = -1;

var sock = io.connect(null, {port: location.port, rememberTransport: false});

sock.on("goal", function(socketData) {
	response = JSON.parse(socketData);
	var new_goal_stars = response["goal_stars"];
	// Update majorana stars
	if (new_goal_stars.length == goal_stars.length) {
		for (i = 0; i < goal_stars.length; ++i) {
			goal_stars[i].position.set(new_goal_stars[i][0], new_goal_stars[i][1], new_goal_stars[i][2]);
		}
	} else {
		for(i = 0; i < goal_stars.length; ++i) {
			scene.remove(goal_stars[i]);
		}
		goal_stars = [];
		for(i = 0; i < new_goal_stars.length; ++i) {
			var star_geometry = new THREE.SphereGeometry(0.1, 32, 32);
			var star_material = new THREE.MeshPhongMaterial({color: 0xff0000});
			var star = new THREE.Mesh(star_geometry, star_material);
			star.position.set(new_goal_stars[i][0], new_goal_stars[i][1], new_goal_stars[i][2]);
			goal_stars.push(star);
			scene.add(star);
		}
	}
});


function textify(message) {
 var loader = new THREE.FontLoader();
 font = loader.load("static/helvetiker_regular.typeface.js",
 			function (font) {
 				 createText(font, message);
 			});
}

function createText(font, message) {
	textGeo = new THREE.TextGeometry(message, {
	  font: font,
	  size: 1,
	  height: 0.01,
	  curveSegments: 10,
	  weight: "normal",
	  bevelThickness: 0.05,
	  bevelSize: 0.01,
	  bevelSegments: 3,
	  bevelEnabled: true,
	  font:font
	});
	textGeo.computeBoundingBox();
	textGeo.computeVertexNormals();
	var text = new THREE.Mesh(textGeo, new THREE.MeshLambertMaterial({color: 0xff3300}));
	text.position.x = -textGeo.boundingBox.max.x/2;
	text.castShadow = true;
	scene.add(text);
}
//textify("WIN!");
var winning = 0;

sock.on("update", function(socketData) {
	response = JSON.parse(socketData);
	var new_majorana_stars = response["surface_stars"];
	var new_mixed_stars = response["inner_stars"];
	var new_me = response["player_id"];
	var new_player_colors = response["player_colors"];
	var new_close = response["close"];
	var new_win = response["win"];

	if (new_win == 1) {
		winning = 1;
	}


	sphere.material.opacity = new_close;
	//console.log(new_close);

	// Update majorana stars
	if (new_majorana_stars.length == majorana_stars.length) {
		for (i = 0; i < majorana_stars.length; ++i) {
			majorana_stars[i].position.set(new_majorana_stars[i][0], new_majorana_stars[i][1], new_majorana_stars[i][2]);
		}
	} else {
		for(i = 0; i < majorana_stars.length; ++i) {
			scene.remove(majorana_stars[i]);
		}
		majorana_stars = [];
		for(i = 0; i < new_majorana_stars.length; ++i) {
			var star_geometry = new THREE.SphereGeometry(0.1, 32, 32);
			var star_material = new THREE.MeshPhongMaterial({color: 0xffffff});
			var star = new THREE.Mesh(star_geometry, star_material);
			star.position.set(new_majorana_stars[i][0], new_majorana_stars[i][1], new_majorana_stars[i][2]);
			majorana_stars.push(star);
			scene.add(star);
		}
	}

	// Update mixed stars
	if (new_mixed_stars.length == mixed_stars.length) {
		for (i = 0; i < mixed_stars.length; ++i) {
			mixed_stars[i].position.set(new_mixed_stars[i][0], new_mixed_stars[i][1], new_mixed_stars[i][2]);
		}
	} else {
		for(i = 0; i < mixed_stars.length; ++i) {
			scene.remove(mixed_stars[i]);
		}
		mixed_stars = [];
		for(i = 0; i < new_mixed_stars.length; ++i) {
			var star_geometry = new THREE.SphereGeometry(0.2, 32, 32);
			var star_material = new THREE.MeshPhongMaterial({roughness: 1, color: new THREE.Color(new_player_colors[i][0], new_player_colors[i][1], new_player_colors[i][2])});
			star_material.side = THREE.BackSide;
			var star = new THREE.Mesh(star_geometry, star_material);
			star.position.set(new_mixed_stars[i][0], new_mixed_stars[i][1], new_mixed_stars[i][2]);
			mixed_stars.push(star);
			scene.add(star);
		}
	}

	// Update camera
	if (camera_mode == "inner") {
		//me = new_me;
		camera.position.set(new_mixed_stars[me][0], new_mixed_stars[me][1], new_mixed_stars[me][2]);
		for(i = 0; i < mixed_stars.length; ++i) {
			mixed_stars[i].material.wireframe=false;
			if (i != me) {
				mixed_stars[i].visible = true;
				if (i == other_selected) {
					mixed_stars[i].material.color.setHex(0x000000);
				} else {
					mixed_stars[i].material.color.setRGB(new_player_colors[i][0], new_player_colors[i][1], new_player_colors[i][2]);
				}
			} else {
				mixed_stars[i].visible = false;
			}
		} 
		if (changed) {
			camera.lookAt(0,0,0);
			changed = false;
		}
	} else if(camera_mode == "sphere") {
		for(i = 0; i < mixed_stars.length; ++i) {
			mixed_stars[i].visible = true;
			if (i == me) {
				//mixed_stars[i].material.color.setHex(0xffffff);
				mixed_stars[i].material.wireframe = true;
			} else if (i == other_selected) {
				mixed_stars[i].material.color.setHex(0x000000);
				mixed_stars[i].material.wireframe = false;
			} else {
				mixed_stars[i].material.color.setRGB(new_player_colors[i][0], new_player_colors[i][1], new_player_colors[i][2]);
				mixed_stars[i].material.wireframe = false;
			}

		} 
	}
});

var counter = 0;
var won = false;
function animate () {
	if (winning == 1 && won == false) {
		createText("WIN!");
		won = true;
	}


	var gamepads = navigator.getGamepads ? navigator.getGamepads() : (navigator.webkitGetGamepads ? navigator.webkitGetGamepads : []);
	for (var i = 0; i < gamepads.length; i++) {
	    var gp = gamepads[i];
	    if (gp) {
	    	if(gp["buttons"][0].pressed == true) {
	    		console.log("A");
	    		if (last != "A") {
	    			if (other_selected == -1) {
	    				if (me != 0) {
	    					other_selected = 0;
	    				} else {
	    					other_selected = 1;
	    				}
	    			} else {
	    				if(other_selected < mixed_stars.length-1) {
	    					other_selected += 1;
	    					if (other_selected == me) {
	    						if (other_selected < mixed_stars.length-1) {
	    							other_selected += 1;
	    						} else {
	    							other_selected = -1;
	    						}
	    					}
	    				} else {
	    					other_selected = -1;
	    				}
	    			}
	    		}
	    		last = "A";
	    	} else if(gp["buttons"][1].pressed == true) {
	    		console.log("B");
	    		if (last != "B") {
	    			sock.emit("cmd", {"type": "more_qubits"});
	    		}
	    		last = "B";
	    	} else if(gp["buttons"][2].pressed == true) {
	    		console.log("X");
	    	} else if(gp["buttons"][3].pressed == true) {
	    		console.log("Y");
	    		if (last != "Y") {
	    			sock.emit("cmd", {"type": "fewer_qubits"});
	    		}
	    		last = "Y";
	    	} else if(gp["buttons"][4].pressed == true) {
	    		console.log("LB");
	    		if (last != "LB") {
		    		camera_mode = "sphere";
		    		camera.position.set(0,0,1.5);
		    	}
		    	last = "LB";
		    	other_selected = -1;
	    	} else if(gp["buttons"][5].pressed == true) {
	    		console.log("RB");
	    		if (last != "RB") {
	    			camera_mode = "inner";
	    			camera.lookAt(0,0,0);
	    		}
	    		last = "RB";
	    		other_selected = -1;
	    	} else if(gp["buttons"][6].pressed == true) {
	    		console.log("LPRESS");
	    	} else if(gp["buttons"][7].pressed == true) {
	    		console.log("RPRESS");
	    	} else if(gp["buttons"][8].pressed == true) {
	    		console.log("START")
	    		if (last != "START") {
	    			sock.emit("cmd", {"type": "new"});
	    		}
	    		last = "START";
	    	} else if(gp["buttons"][9].pressed == true) {
	    		console.log("BACK");
	    		if (last != "BACK") {
	    			sock.emit("cmd", {"type": "reset"});
	    		}
	    		last = "BACK";
	    	} else if(gp["buttons"][10].pressed == true) {
	    		console.log("HOME");
	    		if (last != "HOME") {
	    			help = document.getElementById("help");
    				help.style.display = help.style.display == "none" ? "block" : "none";
	    		}
	    		last = "HOME";
	    	} else if(gp["buttons"][11].pressed == true) {
	    		console.log("UP");
	    	} else if(gp["buttons"][12].pressed == true) {
	    		console.log("DOWN");
	    	} else if(gp["buttons"][13].pressed == true) {
	    		console.log("LEFT");
	    		if (last != "LEFT") {
		    		if (me > 0) {
		    			me -= 1;
		    		} else {
		    			me = mixed_stars.length-1;
		    		}
		    		camera.lookAt(0,0,0);
		    		changed = true;
		    		other_selected = -1;
		    	}
		    	last = "LEFT";
	    	} else if(gp["buttons"][14].pressed == true) {
	    		if (last != "RIGHT") {
		    		if (me < mixed_stars.length-1) {
		    			me += 1;
		    		} else {
		    			me = 0;
		    		}
		    		camera.lookAt(0,0,0);
		    		changed = true;	
		    		other_selected = -1;
		    	}
		    	last = "RIGHT";
	    	} else {
	    		last = "";
	    	}


	    	// gp.axes[0] : left joy horizontal
	    	// gp.axes[1] : left joy vertical
	    	// gp.axes[2] : LT (X)
	    	// gp.axes[3] : right joy horizontal (Y)
	    	// gp.axes[4] : right joy vertical (X)
	    	// gp.axes[5] : RT (Y)
	    	// gp.axes[6]
	    	//sphere.position.set(gp.axes[0], -1*gp.axes[1], 0);
	    	//camera.lookAt(gp.axes[4], -1*gp.axes[5])
	    	if (camera_mode == "inner") {
	    		camera.rotation.y += 0.02*gp.axes[0];
	    		camera.rotation.x -= 0.02*gp.axes[1];
	    	} else if (camera_mode == "sphere") {
	    		camera.lookAt(new THREE.Vector3(0,0,0));
	    		
	    		var xQ = new THREE.Quaternion();
				xQ.setFromAxisAngle( new THREE.Vector3(1, 0, 0), 0.05*gp.axes[1]);
				var yQ = new THREE.Quaternion();
				yQ.setFromAxisAngle( new THREE.Vector3(0, 1, 0), -0.05*gp.axes[0]);

	    		camera.position.applyQuaternion(xQ);
	    		camera.position.applyQuaternion(yQ);

	    		//var x = camera.position.x,
   				//y = camera.position.y,
    			//z = camera.position.z;
    			//camera.position.x = x * Math.cos(gp.axes[0]) + z * Math.sin(gp.axes[0]);
    			//camera.position.z = z * Math.cos(gp.axes[0]) - x * Math.sin(gp.axes[0]);


				//camera.position.y = y * Math.cos(gp.axes[1]) - z * Math.sin(gp.axes[1]);
    			//camera.position.z = y * Math.sin(gp.axes[1]) + z * Math.cos(gp.axes[1]);

	    		//camera.position.x = camera.position.z*2*Math.cos(gp.axes[0]);
	    		//camera.position.z = camera.positoin.x*2*Math.sin(gp.axes[0]);
	    		//var quaternion = new THREE.Quaternion();
				//quaternion.setFromAxisAngle( new THREE.Vector3(0.01*gp.axes[0], -0.01*gp.axes[1], 0), 0.001 );
	    		//camera.position.set(camera.position.applyQuaternion(quaternion));

	    		

	    	}

	    	//var lookAtVector = new THREE.Vector3(camera.matrix[8], camera.matrix[9], camera.matrix[10]);
	    	
	    	if (counter % 2 == 0) {
	    		//if ( (gp.axes[4] > 0.00005 || gp.axes[4] < -0.00005) && (gp.axes[5] > 0.001 || gp.axes[5] < -0.001) ) {
		    	var rot = new THREE.Vector3(gp.axes[4], -1*gp.axes[3], 0)
			    rot.applyQuaternion(camera.quaternion);
			    sock.emit("qubit_rotation", {"who" : me, "rot": [rot.x, rot.y, rot.z]})
				//}

				if (other_selected != -1) {
					sock.emit("entangle_qubits", {"a": other_selected, "b": me, "dt": (gp.axes[5]/2 + 0.5), "inverse": false})
					sock.emit("entangle_qubits", {"a": other_selected, "b": me, "dt": (gp.axes[2]/2 + 0.5), "inverse": true})
				}
				if (counter == 144) {
					counter = 0;
				}
			}
			counter += 1;


	    	//camera.rotation.z += 0.01*(gp.axes[5] + 1);
	    	//camera.position.set(gp.axes[0], -1*gp.axes[1], gp.axes[5]);
	    	//camera.lookAt(gp.axes[3], gp.axes[4], gp.axes[2]);
	    	//if (mixed_stars != []) {
	    	//	camera.position = mixed_stars[me].position;
	    	//}
	    	//camera.lookAt(2, 2, 2);

	    	//console.log(gp)
	    	//console.log("***Gamepad connected at index " + gp.index + ": " + gp.id +
	        //". It has " + gp.buttons.length + " buttons and " + gp.axes.length + " axes.");
	    }
	}
	requestAnimationFrame(animate);
	//camera_controls.update();
	renderer.render(scene, camera);
};
animate();
