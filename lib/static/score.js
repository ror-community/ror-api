$(document).ready(function () {

    $('#select-affn').click(function () {
        $('#affn').val('');
        $('#affn').attr('placeholder', 'Fetching random affiliation...');
        $.getJSON(
            'http://api.crossref.org/works?filter=has-affiliation:true&sample=1',
            function (data) {
                $.each(data["message"]["items"], function (i, work) {
                    author = null;
                    $.each(["author", "editor"], function (x, role) {
                        $.each(work[role], function (v, c) {
                            if (c["affiliation"] !== null)
                                author = c;
                            return false;

                        });
                        return (author !== null);
                    });
                    $('#affn').val(author["affiliation"][0]["name"]);
                });
            }
        );
        return false;
    });

    var compareListTemplate = Hogan.compile(
        '<label class="custom-control custom-radio">' +
        '<input id="radioStacked1" name="result-{{dataset}}" value="{{value}}" type="radio" class="custom-control-input">' +
        '<span class="custom-control-indicator"></span>' +
        '<span class="custom-control-description">{{name}}</span></label>'
    );

    $('#compare').click(function () {
        $('#score').attr("disabled", "disabled");
        $.each( Object.keys(DATASETS), function (i, dataset) {
            $('#dataset-' + dataset).html("Querying...");
            $.getJSON(
                '/search',
                {
                    index: 'org-id-' + dataset,
                    q: $('#affn').val()
                },
                function (data) {
                    var html = '';
                    $(data).slice(0, 5).each(function (i, result) {
                        result["dataset"] = dataset;
                        result["value"] = (10 - i * 2);
                        html += compareListTemplate.render(result);
                    });
                    html += compareListTemplate.render({
                        name: "None of the above",
                        dataset: dataset,
                        value: 0
                    });
                    $('#dataset-' + dataset).html(html);
                }
            );

        });
        $('#score').removeAttr("disabled");
        return false;
    });

    $('#score').click( function() {
        if ($("input:checked").length < Object.keys(DATASETS).length ) {
            alert("Please select an answer for each dataset");
            return false;
        };

        $('#score').attr("disabled", "disabled");
        $("#count").html( parseInt( $("#count").text() ) + 1 );

        $.each( Object.keys(DATASETS), function (i, dataset) {
            current = parseInt( $("#dataset-score-" + dataset).text() );
            increment = parseInt( $("input[name='result-" + dataset + "']:checked").val() );
            $("#dataset-score-" + dataset).html( current + increment );
        });

        return false;
    });
});