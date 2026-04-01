(function () {
  function toggleJudgeModelFields() {
    const actionSelects = Array.from(document.querySelectorAll('select[name="action"]'));
    const judgeModelSelects = Array.from(document.querySelectorAll('select[name="judge_model"]'));
    const shouldShowJudgeModel = actionSelects.some(function (select) {
      return select.value === 'judge_selected_battles';
    });

    judgeModelSelects.forEach(function (select) {
      const container = select.closest('label') || select.parentElement;
      if (!container) {
        return;
      }

      container.style.display = shouldShowJudgeModel ? '' : 'none';
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    toggleJudgeModelFields();
    document.querySelectorAll('select[name="action"]').forEach(function (select) {
      select.addEventListener('change', toggleJudgeModelFields);
    });
  });
})();
