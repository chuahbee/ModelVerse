document.addEventListener("DOMContentLoaded", function () {
  // 删除按钮逻辑
  document.querySelectorAll(".delete-inline").forEach(button => {
    button.addEventListener("click", () => {
      const row = button.closest("tr");
      const checkbox = row.querySelector('input[type="checkbox"][name$="DELETE"]');
      if (checkbox) {
        checkbox.checked = true;
        row.style.display = "none";  // 隐藏这一行
      }
    });
  });

  // Add another row 逻辑
  const addRowButton = document.querySelector(".add-inline");
  if (addRowButton) {
    addRowButton.addEventListener("click", function (e) {
      e.preventDefault();

      const table = document.querySelector("table");
      const totalForms = document.querySelector("#id_productattribute_set-TOTAL_FORMS");
      const formIdx = parseInt(totalForms.value);
      const emptyRow = document.querySelector("tr.empty-form");

      if (emptyRow) {
        const newRow = emptyRow.cloneNode(true);
        newRow.classList.remove("empty-form");
        newRow.classList.add("dynamic-form");

        // 替换索引
        newRow.innerHTML = newRow.innerHTML.replace(/__prefix__/g, formIdx);
        totalForms.value = formIdx + 1;

        table.querySelector("tbody").appendChild(newRow);
      }
    });
  }
});
