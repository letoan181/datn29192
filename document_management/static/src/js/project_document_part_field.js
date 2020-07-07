$('.document_project_name').on('change', function () {
    if ($(this).val().length > 0) {
        $('.group_document_project_part').show()
    } else {
        $('.group_document_project_part').find('button').each(function (key, value) {
            if($(this).attr('name') == 'delete') {
                $(this).click()
            }
        });
        $('.group_document_project_part').hide()
    }
});