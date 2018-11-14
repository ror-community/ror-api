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

    var compareListTemplate = Hogan.compile('<li>{{name}}, {{country}}.<br><span class="text-muted"><small>{{id}}, {{score}}</small></span></li>');

    $('#compare').click(function () {
        $.each( Object.keys(DATASETS), function (i, dataset) {
            console.log(dataset)
            $('#dataset-' + dataset).html("<ul><li>Querying...</li></ul>");
            $.getJSON(
                '/search',
                {
                    index: 'org-id-' + dataset,
                    q: $('#affn').val()
                },
                function (data) {
                    var html = '<ul>';
                    $(data).slice(0, 5).each(function (i, result) {
                        html += compareListTemplate.render(result);
                    });
                    html += '</ul>';
                    $('#dataset-' + dataset).html(html);
                }
            );

        });
        return false;
    });


});