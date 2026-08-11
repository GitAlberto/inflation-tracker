#!/usr/bin/env bash
# =============================================================================
# C12 — Lancement de la suite de tests complète — inflation-tracker
# =============================================================================
# Exécute les 5 fichiers de tests dans l'ordre logique et affiche un bilan
# structuré (passés / échoués / sautés) en fin de session, prêt pour capture.
#
# Usage :
#   bash run_tests.sh               # affichage terminal
#   bash run_tests.sh --save        # + sauvegarde dans tests/resultats_tests.txt
#
# Issue GitHub : #18 (C12)
# =============================================================================

# --- Couleurs ANSI ---
GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
RESET=$'\033[0m'

# --- Interpréteur Python (venv prioritaire) ---
PYTHON=".venv/Scripts/python"
if [ ! -f "$PYTHON" ] && [ ! -f "${PYTHON}.exe" ]; then
    PYTHON="python"
fi

PYTEST="$PYTHON -m pytest"
OPTS="-v --tb=short"
SAVE=false
OUTPUT_FILE="tests/resultats_tests.txt"

for arg in "$@"; do
    case $arg in
        --save) SAVE=true ;;
    esac
done

# --- Définition des 5 suites ---
SUITE_FILES=(
    "tests/test_collect.py"
    "tests/test_aggregate.py"
    "tests/test_model.py"
    "tests/test_api.py"
    "tests/test_api_model.py"
)
SUITE_LABELS=(
    "C1/C3  Collecteur ETL CSV"
    "C3     Pipeline agrégation"
    "C8     Modèle Prophet"
    "C5     API data REST"
    "C9     API modèle REST"
)

# --- Tableaux de résultats (remplis pendant l'exécution) ---
SUITE_PASSED=()
SUITE_FAILED=()
SUITE_SKIPPED=()
SUITE_EXIT=()

SEP="=================================================================="

# =============================================================================
# EXÉCUTION
# =============================================================================

main() {
    echo ""
    echo "${BOLD}${SEP}${RESET}"
    echo "${BOLD}  INFLATION-TRACKER — Suite de tests C12${RESET}"
    echo "${DIM}  $(date '+%Y-%m-%d %H:%M:%S')${RESET}"
    echo "${BOLD}${SEP}${RESET}"
    echo ""

    for i in 0 1 2 3 4; do
        file="${SUITE_FILES[$i]}"
        label="${SUITE_LABELS[$i]}"

        echo "${CYAN}── $((i+1))/5  $label${RESET}"
        echo "${DIM}   $file${RESET}"
        echo ""

        # Exécution et capture complète de la sortie
        output=$($PYTEST $OPTS "$file" 2>&1)
        exit_code=$?
        SUITE_EXIT+=($exit_code)

        echo "$output"
        echo ""

        # Extraction des compteurs depuis la ligne de résumé pytest
        # Exemples : "16 passed in 2s" / "3 failed, 13 passed, 2 skipped in 1s"
        p=$(echo "$output" | grep -oE '[0-9]+ passed'  | grep -oE '^[0-9]+' | tail -1)
        f=$(echo "$output" | grep -oE '[0-9]+ failed'  | grep -oE '^[0-9]+' | tail -1)
        s=$(echo "$output" | grep -oE '[0-9]+ skipped' | grep -oE '^[0-9]+' | tail -1)

        SUITE_PASSED+=(${p:-0})
        SUITE_FAILED+=(${f:-0})
        SUITE_SKIPPED+=(${s:-0})
    done

    # ==========================================================================
    # BILAN FINAL
    # ==========================================================================

    total_passed=0; total_failed=0; total_skipped=0
    nb_ok=0; nb_fail=0

    for i in 0 1 2 3 4; do
        total_passed=$((total_passed  + ${SUITE_PASSED[$i]}))
        total_failed=$((total_failed  + ${SUITE_FAILED[$i]}))
        total_skipped=$((total_skipped + ${SUITE_SKIPPED[$i]}))
        if [ "${SUITE_EXIT[$i]}" -eq 0 ]; then
            nb_ok=$((nb_ok + 1))
        else
            nb_fail=$((nb_fail + 1))
        fi
    done

    echo ""
    echo "${BOLD}${SEP}${RESET}"
    echo "${BOLD}  BILAN C12 — inflation-tracker — $(date '+%Y-%m-%d %H:%M:%S')${RESET}"
    echo "${BOLD}${SEP}${RESET}"
    printf "${BOLD}  %-6s %-26s %8s %9s %8s${RESET}\n" \
        "" "Suite" "Passés" "Échoués" "Sautés"
    echo "  ──────────────────────────────────────────────────────────────"

    for i in 0 1 2 3 4; do
        label="${SUITE_LABELS[$i]}"
        p=${SUITE_PASSED[$i]}
        f=${SUITE_FAILED[$i]}
        s=${SUITE_SKIPPED[$i]}

        if [ "${SUITE_EXIT[$i]}" -eq 0 ]; then
            printf "  ${GREEN}[OK]${RESET}  "
        else
            printf "  ${RED}[KO]${RESET}  "
        fi
        printf "%-26s %8d %9d %8d\n" "$label" "$p" "$f" "$s"
    done

    echo "  ──────────────────────────────────────────────────────────────"
    printf "${BOLD}  %-32s %8d %9d %8d${RESET}\n" \
        "TOTAL  ($nb_ok/5 suites)" "$total_passed" "$total_failed" "$total_skipped"
    echo "${BOLD}${SEP}${RESET}"

    if [ $nb_fail -eq 0 ]; then
        echo "  ${GREEN}${BOLD}✅  $nb_ok/5 suites réussies"\
             "— $total_passed tests passés — 0 en échec${RESET}"
    else
        echo "  ${RED}${BOLD}❌  $nb_fail/5 suite(s) en échec"\
             "— $total_failed test(s) échoué(s)${RESET}"
    fi

    echo "${BOLD}${SEP}${RESET}"
    echo ""
}

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if $SAVE; then
    main 2>&1 | tee "$OUTPUT_FILE"
    echo "→ Résultats sauvegardés dans $OUTPUT_FILE"
else
    main
fi
