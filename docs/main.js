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

    const enableAlertsCheckbox = document.getElementById("enableAlerts");
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

        // Trigger alert if enabled and a nearby signboard is detected
        if (enableAlertsCheckbox.checked) {
            checkNearbySignboards(coords);
        }
    });

    function checkNearbySignboards(userCoords) {
        const nearbySigns = allFeatures.filter(feature => {
            const featureCoords = feature.getGeometry().getCoordinates();
            const distance = ol.sphere.getDistance(userCoords, featureCoords);
            return distance <= 20; // 20 meters range
        });

        if (nearbySigns.length > 0) {
            alert('There are nearby signboards within 20 meters!');
            // Optionally, show details in popup
            const nearbySign = nearbySigns[0];
            const properties = nearbySign.getProperties();
            const imageName = properties.image_name;
            const currentClass = properties.predicted_class;
            const imagePath = `data/icons/${currentClass}.png`;

            popup.innerHTML = `
                <strong>Nearby Sign:</strong><br>
                ${currentClass}<br>
                <img src="${imagePath}" alt="${currentClass}" width="100"><br>
            `;
            overlay.setPosition(userCoords); // Show popup at user location or signboard location
            popup.style.display = 'block';
        }
    }

    document.getElementById("centerOnLocationBtn").addEventListener("click", () => {
        const geometry = positionFeature.getGeometry();
        if (geometry) {
            const coords = geometry.getCoordinates();
            map.getView().animate({ center: coords, zoom: 18, duration: 500 });
        } else {
            alert("Live location not available yet.");
        }
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
            const classes = [...new Set(allFeatures.map(f => f.get('predicted_class')))].sort();
            classes.forEach(cls => {
                const option = document.createElement("option");
                option.value = cls;
                option.textContent = cls;
                signFilter.appendChild(option);
            });
        })
        .catch(error => console.error("❌ Error loading GeoJSON:", error));
};
