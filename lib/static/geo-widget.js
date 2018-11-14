$(document).ready(function () {

    //Reset current value when we change dataset, otherwise we see cached results
    //on first click into the field.
    $('input[type=radio][name=datasets]').on("change", function () {
        $('#org-name').typeahead('val', '');
        $('#debug').html("");
    });

    $("#org-country").on("change", function() {
        $('#org-name').typeahead('val', '');
        $('#debug').html("");
    });

    var orgRemote = new Bloodhound({
        name: 'grid',
        datumTokenizer: function (d) {
            return d.tokens;
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/search?index=org-id-grid&q=%QUERY',
            prepare: function (query, settings) {
                dataset = $("input[name]:checked").val();
                country = $("#org-country").val();
                settings.url = "/search?index=" + dataset + "&country=" + country + "&q=" + encodeURIComponent(query);
                return settings;
            },
            wildcard: "%QUERY"
        },
        dupDetector: function (r, l) {
            return false;
        }
    });

    orgRemote.initialize();

    var suggestionLayout = Hogan.compile('<p>{{name}} <span style="color: grey; font-size: 0.7em;">{{country}}</span></p>');
    var debug = Hogan.compile('<strong>Debug</strong>: Id: {{id}}, Name: {{name}}, Score: {{score}}');
    var notFoundLayout = Hogan.compile('<p>No institutions found</p>');

    $('#org-name').typeahead({minLength: 3}, {
        source: orgRemote.ttAdapter(),
        templates: {
            suggestion: function (d) {
                return suggestionLayout.render(d)
            },
            notFound: function() {
                return notFoundLayout.render();
            }
        },
        displayKey: "name",
        limit: 5
    });

    $('#org-name').bind('typeahead:select', function (ev, suggestion) {
        $("#debug").html(debug.render(suggestion));
    });


    if (navigator.geolocation) {
        $("#org-country").prop("disabled", true);
        navigator.geolocation.getCurrentPosition( function(position) {
            $("#coords-debug").html("" + position.coords.latitude + " " + position.coords.longitude);

            url = "http://api.geonames.org/countryCode?lat=" +
                position.coords.latitude + "&lng=" + position.coords.longitude + "&username=ldodds";

            $.get(url, function(data) {
                $("#org-country option[value="+data+"]").attr("selected", "selected");
                $("#org-country").prop("disabled", false);
                $("#coords-debug").html($("#coords-debug").html() + ", Country: " + data);
            });

        }, function(err) {
            $("#org-country").prop("disabled", false);
            $("#coords-debug").html("Error getting geolocation: " + err.code + " " + err.message);
        });
    }
    else {
        $("#coords-debug").html("Geolocation unavailable");
    }

});
