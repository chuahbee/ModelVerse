(function($) {
    $(document).ready(function(){
        $(document).on('change', '.dynamic-product_attributes select[name$="attribute"]', function () {
            var $attributeSelect = $(this);
            var attributeId = $attributeSelect.val();
            var $row = $attributeSelect.closest('.form-row, .grp-row');  // grappelli 用 .grp-row
            var $valueSelect = $row.find('select[name$="value"]');

            if (attributeId) {
                $.ajax({
                    url: "/admin/get_attribute_values/",
                    data: { attribute_id: attributeId },
                    success: function (data) {
                        $valueSelect.empty();
                        $valueSelect.append(
                            $('<option></option>').val('').text('---------')
                        );
                        $.each(data, function (idx, item) {
                            $valueSelect.append(
                                $('<option></option>').attr('value', item.id).text(item.text)
                            );
                        });
                    }
                });
            } else {
                $valueSelect.empty();
                $valueSelect.append(
                    $('<option></option>').val('').text('---------')
                );
            }
        });
    });
})(django.jQuery);
