// Wait for the DOM to fully load
document.addEventListener("DOMContentLoaded", function() {
    // Initialize the Google Map
    initMap();

    // Existing JavaScript for Interactive Section
    const actionButton = document.getElementById('actionButton');
    const resultText = document.getElementById('resultText');

    actionButton.addEventListener('click', function() {
        resultText.textContent = "You clicked the button!";
    });
});

// Function to Initialize the Google Map
function initMap() {
    // Define the center of the map (coordinates from your original link)
    var mapCenter = { lat: -27.65147395225832, lng: 152.7716634831431 };

    // Create a new map instance
    var map = new google.maps.Map(document.getElementById('map'), {
        center: mapCenter,
        zoom: 15,  // Adjust the zoom level as needed
        mapTypeId: 'roadmap'  // Other options: 'satellite', 'hybrid', 'terrain'
    });

    // Load the first KMZ Layer
    var kmlLayer1 = new google.maps.KmlLayer({
        url: window.location.origin + '/kml/firstdata.kmz',  // Relative path to your first KMZ file
        map: map,
        preserveViewport: true,  // Prevents the map from resetting to default center and zoom
        suppressInfoWindows: false,  // Set to true to disable info windows
        clickable: true  // Set to false to make features non-clickable
    });

    // Load the second KMZ Layer
    var kmlLayer2 = new google.maps.KmlLayer({
        url: window.location.origin + '/kml/firstdata1.kmz',  // Relative path to your second KMZ file
        map: map,
        preserveViewport: true,
        suppressInfoWindows: false,
        clickable: true
    });

    // Optional: Add Event Listeners for KMZ Layers to Handle Loading Status
    kmlLayer1.addListener('status_changed', function() {
        if (kmlLayer1.getStatus() !== google.maps.KmlLayerStatus.OK) {
            console.error('Failed to load the first KMZ layer:', kmlLayer1.getStatus());
        }
    });

    kmlLayer2.addListener('status_changed', function() {
        if (kmlLayer2.getStatus() !== google.maps.KmlLayerStatus.OK) {
            console.error('Failed to load the second KMZ layer:', kmlLayer2.getStatus());
        }
    });

    // Layer Toggle Functionality (Optional)
    var toggleLayer1 = document.getElementById('toggleLayer1');
    var toggleLayer2 = document.getElementById('toggleLayer2');

    if (toggleLayer1 && toggleLayer2) {
        toggleLayer1.addEventListener('change', function() {
            kmlLayer1.setMap(this.checked ? map : null);
        });

        toggleLayer2.addEventListener('change', function() {
            kmlLayer2.setMap(this.checked ? map : null);
        });
    }

    // Adding a Custom Marker (Optional)
    var customMarker = new google.maps.Marker({
        position: { lat: -27.6515, lng: 152.7717 },  // Replace with desired coordinates
        map: map,
        title: 'Custom Location',
        icon: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png'  // Optional: Custom icon
    });

    // Info Window for Custom Marker (Optional)
    var infoWindow = new google.maps.InfoWindow({
        content: '<h3>Custom Location</h3><p>Details about this location.</p>'
    });

    customMarker.addListener('click', function() {
        infoWindow.open(map, customMarker);
    });
}
