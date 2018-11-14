$(document).ready(function () {

    //Reset current value when we change dataset, otherwise we see cached results
    //on first click into the field.
    $('input[type=radio][name=datasets]').on("change", function () {
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
                settings.url = "/search?index=" + dataset + "&q=" + encodeURIComponent(query);
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

});
