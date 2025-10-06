(function($) {
    $(document).ready(function(){

        // 自动触发 change，处理已有行
        $('.dynamic-product_attributes select[name$="attribute"]').each(function(){
            if ($(this).val()) {
                $(this).trigger('change');
            }
        });

        $(document).on('change', '.dynamic-product_attributes select[name$="attribute"]', function () {
            var $attributeSelect = $(this);
            var attributeId = $attributeSelect.val();
            var $row = $attributeSelect.closest('.form-row, .grp-row');
            var $valueSelect = $row.find('select[name$="value"]');

            if (attributeId) {
                $.ajax({
                    url: "/ajax/get-attribute-values/",
                    data: { attribute_id: attributeId },
                    success: function (data) {
                        var oldValue = $valueSelect.data('selected-value');

                        $valueSelect.empty();
                        $valueSelect.append(
                            $('<option></option>').val('').text('---------')
                        );

                        $.each(data, function (idx, item) {
                            var option = $('<option></option>').attr('value', item.id).text(item.text);
                            if (oldValue && item.id == oldValue) {
                                option.attr('selected', 'selected');
                            }
                            $valueSelect.append(option);
                        });

                        $valueSelect.data('selected-value', '');
                    },
                    error: function(xhr, status, error) {
                        alert("Error loading attribute values: " + error);
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
