window.onload = function () {
    const osmLayer = new ol.layer.Tile({ source: new ol.source.OSM(), visible: true });
    const satelliteLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}' }),
        visible: false
    });
    const cartoDarkLayer = new ol.layer.Tile({
        source: new ol.source.XYZ({
            url: 'https://{a-c}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            attributions: '© OpenStreetMap contributors, © CARTO',
            crossOrigin: 'anonymous'
        }),
        visible: false
    });

    const map = new ol.Map({
        target: "map",
        layers: [osmLayer, satelliteLayer, cartoDarkLayer],
        view: new ol.View({ center: ol.proj.fromLonLat([79.529158, 17.983326]), zoom: 18 })
    });

    document.getElementById('basemapSelect').addEventListener('change', function () {
        const selected = this.value;
        osmLayer.setVisible(selected === 'osm');
        satelliteLayer.setVisible(selected === 'satellite');
        cartoDarkLayer.setVisible(selected === 'carto');
    });

    const signFilter = document.getElementById("signFilter");
    const enableEditingCheckbox = document.getElementById("enableEditing");
    const popup = document.getElementById("popup");

    const overlay = new ol.Overlay({
        element: popup,
        positioning: 'bottom-center',
        stopEvent: true
    });
    map.addOverlay(overlay);

    const liveLocationSource = new ol.source.Vector();
    const liveLocationLayer = new ol.layer.Vector({ source: liveLocationSource, zIndex: 1000 });
    map.addLayer(liveLocationLayer);

    const positionFeature = new ol.Feature({ geometry: null });
    positionFeature.set('isLiveLocation', true);
    positionFeature.setStyle(new ol.style.Style({
        image: new ol.style.Circle({
            radius: 6,
            fill: new ol.style.Fill({ color: '#4285F4' }), // Google Maps blue
            stroke: new ol.style.Stroke({ color: 'white', width: 2 })
        })
    }));


    const accuracyFeature = new ol.Feature({ geometry: null });
    accuracyFeature.set('isLiveLocation', true);
    accuracyFeature.setStyle(new ol.style.Style({
        fill: new ol.style.Fill({ color: 'rgba(66, 133, 244, 0.15)' }),
        stroke: new ol.style.Stroke({ color: 'rgba(66, 133, 244, 0.5)', width: 1 })
    }));


    liveLocationSource.addFeatures([accuracyFeature, positionFeature]);

    let hasCentered = false;
    navigator.geolocation.watchPosition(function (pos) {
        const coords = ol.proj.fromLonLat([pos.coords.longitude, pos.coords.latitude]);
        positionFeature.setGeometry(new ol.geom.Point(coords));
        const accuracyCircle = ol.geom.Polygon.circular(ol.proj.get('EPSG:3857'), coords, pos.coords.accuracy, 64);
        accuracyFeature.setGeometry(accuracyCircle);
        if (!hasCentered) {
            map.getView().setCenter(coords);
            hasCentered = true;
        }
    });

    document.getElementById("centerOnLocationBtn").addEventListener("click", () => {
    const geometry = positionFeature.getGeometry();
    if (geometry) {
        const coords = geometry.getCoordinates();
        map.getView().animate({ center: coords, zoom: 18, duration: 500 });
    } else {
        alert("Live location not available yet.");
    }
    });


map.on('click', function (event) {
    map.forEachFeatureAtPixel(event.pixel, function (feature) {
        if (feature.get('isLiveLocation')) {
            // Get the coordinates of the live location point
            const coords = ol.proj.toLonLat(positionFeature.getGeometry().getCoordinates());

            // Format the coordinates to 2 decimal places
            const formattedLatitude = coords[1].toFixed(2);
            const formattedLongitude = coords[0].toFixed(2);

            // Show the coordinates in the popup
            popup.innerHTML = `
                <strong>Live Location:</strong><br>
                Latitude: ${formattedLatitude}<br>
                Longitude: ${formattedLongitude}<br>
            `;
            overlay.setPosition(event.coordinate);
            popup.style.display = 'block';
        }
    });
});


    let allFeatures = [];
    fetch('data/predictions.geojson')
        .then(response => response.json())
        .then(data => {
            allFeatures = new ol.format.GeoJSON().readFeatures(data, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857'
            });

            const vectorSource = new ol.source.Vector({ features: allFeatures });

            const styleFunction = function (feature) {
                return new ol.style.Style({
                    image: new ol.style.Circle({
                        radius: 8,
                        fill: new ol.style.Fill({ color: 'red' }),
                        stroke: new ol.style.Stroke({ color: 'white', width: 2 })
                    }),
                    text: new ol.style.Text({
                        text: feature.get('predicted_class'),
                        offsetY: -15,
                        font: '12px Arial',
                        fill: new ol.style.Fill({ color: 'black' }),
                        stroke: new ol.style.Stroke({ color: 'white', width: 3 })
                    })
                });
            };

            const vectorLayer = new ol.layer.Vector({ source: vectorSource, style: styleFunction });
            map.addLayer(vectorLayer);

    // Populate sign filter
    const signFilter = document.getElementById("signFilter");
    const fromDate = document.getElementById("fromDate");
    const toDate = document.getElementById("toDate");

    const classes = [...new Set(allFeatures.map(f => f.get('predicted_class')))].sort();
    classes.forEach(cls => {
        const option = document.createElement("option");
        option.value = cls;
        option.textContent = cls;
        signFilter.appendChild(option);
    });

            function applyFilters() {
                const selectedClass = signFilter.value;
                const from = new Date(fromDate.value);
                const to = new Date(toDate.value);

                const filtered = allFeatures.filter(f => {
                    const matchClass = selectedClass === "all" || f.get('predicted_class') === selectedClass;
                    const featureTime = new Date(f.get('timestamp'));
                    const matchDate = (!fromDate.value || featureTime >= from) && (!toDate.value || featureTime <= to);
                    return matchClass && matchDate;
                });

                vectorSource.clear();
                vectorSource.addFeatures(filtered);
            }

            signFilter.addEventListener("change", applyFilters);
            fromDate.addEventListener("change", applyFilters);
            toDate.addEventListener("change", applyFilters);

map.on('click', function (event) {
    let clickedFeature = null;

    // Check if a feature was clicked
    map.forEachFeatureAtPixel(event.pixel, function (feature) {
        // If the feature is the live location, store it
        if (feature.get('isLiveLocation')) {
            clickedFeature = feature;
        } else {
            // If it's another feature, store that too
            clickedFeature = feature;
        }
    });

    // If a feature is clicked, handle the popup display
    if (clickedFeature) {
        if (clickedFeature.get('isLiveLocation')) {
            // Handle live location feature click
            const coords = ol.proj.toLonLat(positionFeature.getGeometry().getCoordinates());
            const formattedLatitude = coords[1].toFixed(2);
            const formattedLongitude = coords[0].toFixed(2);

            // Show the live location in the popup
            popup.innerHTML = `
                <strong>Live Location:</strong><br>
                Latitude: ${formattedLatitude}<br>
                Longitude: ${formattedLongitude}<br>
            `;
        } else {
            // Handle other features (traffic signs, etc.)
            const properties = clickedFeature.getProperties();
            const currentClass = properties.predicted_class;
            const imageName = properties.image_name;
            const isEditable = enableEditingCheckbox.checked;
            const imageToggleValue = document.getElementById("imageToggle").value;
            const imagePath = imageToggleValue === "real"
                ? `data/images/${imageName}`
                : `data/icons/${currentClass}.png`;

            popup.innerHTML = `
                <strong>Sign:</strong><br>
                ${isEditable
                    ? `<input type="text" id="editClass" value="${currentClass}" style="width: 120px;"><br>`
                    : `<span>${currentClass}</span><br>`
                }
                <img src="${imagePath}" alt="${currentClass}" width="100"><br>
                ${isEditable ? `<button id="updateClassBtn">Update</button>` : ``}
            `;

            if (isEditable) {
                document.getElementById("updateClassBtn").onclick = () => {
                    const newClass = document.getElementById("editClass").value;
                    clickedFeature.set('predicted_class', newClass);
                    vectorSource.changed();
                    popup.style.display = 'none';
                };
            }
        }

        // Display the popup
        overlay.setPosition(event.coordinate);
        popup.style.display = 'block';
    } else {
        // If no feature is clicked, hide the popup
        overlay.setPosition(undefined);
        popup.style.display = 'none';
    }
});



    document.getElementById('downloadGeoJSON').addEventListener('click', () => {
        const geojsonFormat = new ol.format.GeoJSON();
        const updatedGeoJSON = geojsonFormat.writeFeaturesObject(allFeatures, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857'
        });

                const blob = new Blob([JSON.stringify(updatedGeoJSON, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'updated_predictions.geojson';
                link.click();
            });
        })
        .catch(error => console.error("❌ Error loading GeoJSON:", error));

    document.getElementById('toggleControls').addEventListener("click", () => {
        document.body.classList.toggle("hide-controls");
        document.getElementById('toggleControls').textContent = document.body.classList.contains("hide-controls") ? "Show Controls" : "Hide Controls";
        map.updateSize();
    });
};
