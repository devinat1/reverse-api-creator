#!/bin/bash
# Load Testing Runner Script for CloudCruise
#
# This script provides convenient commands to run different load test scenarios.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
HOST="${HOST:-http://localhost:8000}"
REPORT_DIR="./load_test_reports"

# Print colored message
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage
usage() {
    cat << EOF
CloudCruise Load Testing Runner

Usage: $0 [command] [options]

Commands:
    baseline        Run baseline performance test (gradual ramp-up)
    stress          Run stress test (high load)
    ratelimit       Test rate limiting behavior
    mixed           Run mixed workload test
    ui              Start Locust web UI for manual testing
    kafka           Monitor Kafka consumer lag in real-time
    quick           Quick smoke test (low load, short duration)

Options:
    --host URL      API host URL (default: http://localhost:8000)
    --users N       Number of concurrent users (varies by test)
    --duration S    Test duration in seconds (varies by test)
    --output DIR    Output directory for reports (default: ./load_test_reports)

Examples:
    # Run baseline test
    $0 baseline

    # Run stress test with custom settings
    $0 stress --users 100 --duration 300

    # Start web UI for manual testing
    $0 ui

    # Monitor Kafka lag during test
    $0 kafka

    # Quick smoke test
    $0 quick

EOF
    exit 0
}

# Check if services are running
check_services() {
    print_info "Checking if CloudCruise API is running..."

    if ! curl -s "${HOST}/health" > /dev/null 2>&1; then
        print_error "API not responding at ${HOST}"
        print_info "Make sure the API is running: uvicorn app.main:app --reload"
        exit 1
    fi

    print_success "API is running at ${HOST}"
}

# Create reports directory
setup_reports() {
    mkdir -p "${REPORT_DIR}"
    print_info "Reports will be saved to: ${REPORT_DIR}"
}

# Run baseline test
run_baseline() {
    local users="${1:-20}"
    local duration="${2:-120}"

    print_info "Running BASELINE test..."
    print_info "Users: ${users}, Duration: ${duration}s, Spawn rate: 2 users/s"

    setup_reports
    check_services

    locust \
        -f tests/load/locustfile.py \
        --host="${HOST}" \
        --users="${users}" \
        --spawn-rate=2 \
        --run-time="${duration}s" \
        --headless \
        --html="${REPORT_DIR}/baseline_$(date +%Y%m%d_%H%M%S).html" \
        --csv="${REPORT_DIR}/baseline_$(date +%Y%m%d_%H%M%S)" \
        MixedWorkloadUser

    print_success "Baseline test complete! Check ${REPORT_DIR} for results."
}

# Run stress test
run_stress() {
    local users="${1:-100}"
    local duration="${2:-180}"

    print_info "Running STRESS test..."
    print_info "Users: ${users}, Duration: ${duration}s, Spawn rate: 10 users/s"

    setup_reports
    check_services

    locust \
        -f tests/load/locustfile.py \
        --host="${HOST}" \
        --users="${users}" \
        --spawn-rate=10 \
        --run-time="${duration}s" \
        --headless \
        --html="${REPORT_DIR}/stress_$(date +%Y%m%d_%H%M%S).html" \
        --csv="${REPORT_DIR}/stress_$(date +%Y%m%d_%H%M%S)" \
        MixedWorkloadUser

    print_success "Stress test complete! Check ${REPORT_DIR} for results."
}

# Run rate limit test
run_ratelimit() {
    local users="${1:-30}"
    local duration="${2:-60}"

    print_info "Running RATE LIMIT test..."
    print_info "Users: ${users}, Duration: ${duration}s, Spawn rate: 15 users/s"
    print_warning "This test intentionally triggers rate limits (429 responses)"

    setup_reports
    check_services

    locust \
        -f tests/load/locustfile.py \
        --host="${HOST}" \
        --users="${users}" \
        --spawn-rate=15 \
        --run-time="${duration}s" \
        --headless \
        --html="${REPORT_DIR}/ratelimit_$(date +%Y%m%d_%H%M%S).html" \
        --csv="${REPORT_DIR}/ratelimit_$(date +%Y%m%d_%H%M%S)" \
        RateLimitTestUser

    print_success "Rate limit test complete! Check ${REPORT_DIR} for results."
    print_info "Look for 429 (Too Many Requests) responses in the report."
}

# Run mixed workload test
run_mixed() {
    local users="${1:-50}"
    local duration="${2:-120}"

    print_info "Running MIXED WORKLOAD test..."
    print_info "Users: ${users}, Duration: ${duration}s, Spawn rate: 5 users/s"

    setup_reports
    check_services

    locust \
        -f tests/load/locustfile.py \
        --host="${HOST}" \
        --users="${users}" \
        --spawn-rate=5 \
        --run-time="${duration}s" \
        --headless \
        --html="${REPORT_DIR}/mixed_$(date +%Y%m%d_%H%M%S).html" \
        --csv="${REPORT_DIR}/mixed_$(date +%Y%m%d_%H%M%S)" \
        MixedWorkloadUser

    print_success "Mixed workload test complete! Check ${REPORT_DIR} for results."
}

# Start web UI
run_ui() {
    print_info "Starting Locust Web UI..."
    print_info "Navigate to: http://localhost:8089"
    print_info "Host is set to: ${HOST}"
    print_info "Press Ctrl+C to stop"

    check_services

    locust \
        -f tests/load/locustfile.py \
        --host="${HOST}"
}

# Monitor Kafka
run_kafka_monitor() {
    local duration="${1:-120}"

    print_info "Starting Kafka consumer lag monitor..."
    print_info "Duration: ${duration}s (or Ctrl+C to stop)"
    print_info "Monitoring topic: har-uploads, group: har-processor"

    python3 tests/load/kafka_monitor.py --duration="${duration}"

    print_success "Kafka monitoring complete!"
}

# Run quick smoke test
run_quick() {
    print_info "Running QUICK smoke test..."
    print_info "Users: 5, Duration: 30s, Spawn rate: 1 user/s"

    setup_reports
    check_services

    locust \
        -f tests/load/locustfile.py \
        --host="${HOST}" \
        --users=5 \
        --spawn-rate=1 \
        --run-time=30s \
        --headless \
        --html="${REPORT_DIR}/quick_$(date +%Y%m%d_%H%M%S).html" \
        NormalUser

    print_success "Quick test complete! Check ${REPORT_DIR} for results."
}

# Parse arguments
COMMAND="${1:-help}"
shift || true

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --users)
            USERS="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --output)
            REPORT_DIR="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Execute command
case "${COMMAND}" in
    baseline)
        run_baseline "${USERS}" "${DURATION}"
        ;;
    stress)
        run_stress "${USERS}" "${DURATION}"
        ;;
    ratelimit)
        run_ratelimit "${USERS}" "${DURATION}"
        ;;
    mixed)
        run_mixed "${USERS}" "${DURATION}"
        ;;
    ui)
        run_ui
        ;;
    kafka)
        run_kafka_monitor "${DURATION}"
        ;;
    quick)
        run_quick
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        print_error "Unknown command: ${COMMAND}"
        usage
        ;;
esac
