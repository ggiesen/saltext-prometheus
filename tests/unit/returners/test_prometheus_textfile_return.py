# pylint: disable=unused-argument,invalid-name
import os
import re

import pytest
import salt.utils.files
import salt.version
import saltext.prometheus.returners.prometheus_textfile as prometheus_textfile

from tests.support.mock import patch


@pytest.fixture
def root_dir(tmp_path):
    return str(tmp_path / "root_dir")


@pytest.fixture
def cache_dir(root_dir):
    return os.path.join(root_dir, "cachedir")


@pytest.fixture
def job_ret():
    ret = {
        "jid": "20211109174620871797",
        "return": {
            "cmd_|-echo includeme_|-echo includeme_|-run": {
                "name": "echo includeme",
                "changes": {
                    "pid": 10549,
                    "retcode": 0,
                    "stdout": "includeme",
                    "stderr": "",
                },
                "result": True,
                "comment": 'Command "echo includeme" run',
                "__sls__": "includeme",
                "__run_num__": 0,
                "start_time": "17:46:21.013878",
                "duration": 7.688,
                "__id__": "echo includeme",
            },
            "cmd_|-echo applyme_|-echo applyme_|-run": {
                "name": "echo applyme",
                "changes": {
                    "pid": 10550,
                    "retcode": 0,
                    "stdout": "applyme",
                    "stderr": "",
                },
                "result": None,
                "comment": 'Command "echo applyme" run',
                "__sls__": "applyme",
                "__run_num__": 1,
                "start_time": "17:46:21.021948",
                "duration": 6.007,
                "__id__": "echo applyme",
            },
        },
        "retcode": 0,
        "out": "highstate",
        "id": "d10-master-01.example.local",
        "fun": "state.apply",
        "fun_args": ["applyme"],
        "success": True,
    }
    return ret


@pytest.fixture
def patch_dunders(cache_dir, minion):
    opts = minion.config.copy()
    opts["cachedir"] = cache_dir
    with patch(
        "saltext.prometheus.returners.prometheus_textfile.__opts__", opts, create=True
    ), patch("saltext.prometheus.returners.prometheus_textfile.__salt__", {}, create=True):
        yield


def test_basic_prometheus_output_with_default_options(patch_dunders, job_ret, cache_dir, minion):
    expected = "\n".join(
        sorted(
            [
                "# HELP salt_procs Number of salt minion processes running",
                "# TYPE salt_procs gauge",
                "salt_procs 0.0",
                "# HELP salt_states_succeeded Number of successful states in the run",
                "# TYPE salt_states_succeeded gauge",
                "salt_states_succeeded 2.0",
                "# HELP salt_states_failed Number of failed states in the run",
                "# TYPE salt_states_failed gauge",
                "salt_states_failed 0.0",
                "# HELP salt_states_changed Number of changed states in the run",
                "# TYPE salt_states_changed gauge",
                "salt_states_changed 2.0",
                "# HELP salt_states_total Total states in the run",
                "# TYPE salt_states_total gauge",
                "salt_states_total 2.0",
                "# HELP salt_states_success_pct Percent of successful states in the run",
                "# TYPE salt_states_success_pct gauge",
                "salt_states_success_pct 100.0",
                "# HELP salt_states_failure_pct Percent of failed states in the run",
                "# TYPE salt_states_failure_pct gauge",
                "salt_states_failure_pct 0.0",
                "# HELP salt_states_changed_pct Percent of changed states in the run",
                "# TYPE salt_states_changed_pct gauge",
                "salt_states_changed_pct 100.0",
                "# HELP salt_elapsed_time Time spent for all operations during the state run",
                "# TYPE salt_elapsed_time gauge",
                "salt_elapsed_time 13.695",
                "# HELP salt_last_started Estimated time the state run started",
                "# TYPE salt_last_started gauge",
                "# HELP salt_last_completed Time of last state run completion",
                "# TYPE salt_last_completed gauge",
                "# HELP salt_version Version of installed Salt package",
                "# TYPE salt_version gauge",
                "salt_version {}".format(salt.version.__version__),
                "# HELP salt_version_tagged Version of installed Salt package as a tag",
                "# TYPE salt_version_tagged gauge",
                'salt_version_tagged{{salt_version="{}"}} 1.0'.format(salt.version.__version__),
            ]
        )
    )

    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Drop time-based fields for comparison
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )
    assert salt_prom == expected


@pytest.mark.parametrize(
    "state_name,filename,expected_filename",
    [
        ("aaa", "one", "one-aaa"),
        ("bbb", "one.two", "one-bbb.two"),
        ("ccc", "one.two.three", "one.two-ccc.three"),
        ("ddd", "one.two.three.four", "one.two.three-ddd.four"),
    ],
)
def test_when_add_state_name_is_set_then_correct_output_should_be_in_correct_file(
    patch_dunders,
    state_name,
    filename,
    expected_filename,
    minion,
    cache_dir,
    job_ret,
):
    job_ret["fun_args"][0] = state_name
    prometheus_textfile.__opts__.update(
        {"add_state_name": True, "filename": os.path.join(cache_dir, filename)}
    )

    expected = "\n".join(
        sorted(
            [
                "# HELP salt_procs Number of salt minion processes running",
                "# TYPE salt_procs gauge",
                'salt_procs{{state="{}"}} 0.0'.format(state_name),
                "# HELP salt_states_succeeded Number of successful states in the run",
                "# TYPE salt_states_succeeded gauge",
                'salt_states_succeeded{{state="{}"}} 2.0'.format(state_name),
                "# HELP salt_states_failed Number of failed states in the run",
                "# TYPE salt_states_failed gauge",
                'salt_states_failed{{state="{}"}} 0.0'.format(state_name),
                "# HELP salt_states_changed Number of changed states in the run",
                "# TYPE salt_states_changed gauge",
                'salt_states_changed{{state="{}"}} 2.0'.format(state_name),
                "# HELP salt_states_total Total states in the run",
                "# TYPE salt_states_total gauge",
                'salt_states_total{{state="{}"}} 2.0'.format(state_name),
                "# HELP salt_states_success_pct Percent of successful states in the run",
                "# TYPE salt_states_success_pct gauge",
                'salt_states_success_pct{{state="{}"}} 100.0'.format(state_name),
                "# HELP salt_states_failure_pct Percent of failed states in the run",
                "# TYPE salt_states_failure_pct gauge",
                'salt_states_failure_pct{{state="{}"}} 0.0'.format(state_name),
                "# HELP salt_states_changed_pct Percent of changed states in the run",
                "# TYPE salt_states_changed_pct gauge",
                'salt_states_changed_pct{{state="{}"}} 100.0'.format(state_name),
                "# HELP salt_elapsed_time Time spent for all operations during the state run",
                "# TYPE salt_elapsed_time gauge",
                'salt_elapsed_time{{state="{}"}} 13.695'.format(state_name),
                "# HELP salt_last_started Estimated time the state run started",
                "# TYPE salt_last_started gauge",
                "# HELP salt_last_completed Time of last state run completion",
                "# TYPE salt_last_completed gauge",
                "# HELP salt_version Version of installed Salt package",
                "# TYPE salt_version gauge",
                'salt_version{{state="{}"}} {}'.format(state_name, salt.version.__version__),
                "# HELP salt_version_tagged Version of installed Salt package as a tag",
                "# TYPE salt_version_tagged gauge",
                'salt_version_tagged{{salt_version="{}",state="{}"}} 1.0'.format(
                    salt.version.__version__, state_name
                ),
            ]
        )
    )
    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(os.path.join(cache_dir, expected_filename)) as prom_file:
        # use line[:-1] to strip off the newline, but only one. It may be extra
        # paranoid due to how Python file iteration works, but...
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )
    assert salt_prom == expected


def test_prometheus_output_with_show_failed_state_option_and_abort_state_ids(
    patch_dunders, job_ret, cache_dir, minion
):
    job_ret["return"]["cmd_|-echo includeme_|-echo includeme_|-run"]["result"] = False
    prometheus_textfile.__opts__.update({"show_failed_states": True})
    promfile_lines = [
        "# HELP salt_procs Number of salt minion processes running",
        "# TYPE salt_procs gauge",
        "salt_procs 0.0",
        "# HELP salt_states_succeeded Number of successful states in the run",
        "# TYPE salt_states_succeeded gauge",
        "salt_states_succeeded 1.0",
        "# HELP salt_states_failed Number of failed states in the run",
        "# TYPE salt_states_failed gauge",
        "salt_states_failed 1.0",
        "# HELP salt_states_changed Number of changed states in the run",
        "# TYPE salt_states_changed gauge",
        "salt_states_changed 2.0",
        "# HELP salt_states_total Total states in the run",
        "# TYPE salt_states_total gauge",
        "salt_states_total 2.0",
        "# HELP salt_states_success_pct Percent of successful states in the run",
        "# TYPE salt_states_success_pct gauge",
        "salt_states_success_pct 50.0",
        "# HELP salt_states_failure_pct Percent of failed states in the run",
        "# TYPE salt_states_failure_pct gauge",
        "salt_states_failure_pct 50.0",
        "# HELP salt_states_changed_pct Percent of changed states in the run",
        "# TYPE salt_states_changed_pct gauge",
        "salt_states_changed_pct 100.0",
        "# HELP salt_elapsed_time Time spent for all operations during the state run",
        "# TYPE salt_elapsed_time gauge",
        "salt_elapsed_time 13.695",
        "# HELP salt_last_started Estimated time the state run started",
        "# TYPE salt_last_started gauge",
        "# HELP salt_last_completed Time of last state run completion",
        "# TYPE salt_last_completed gauge",
        "# HELP salt_version Version of installed Salt package",
        "# TYPE salt_version gauge",
        "salt_version {}".format(salt.version.__version__),
        "# HELP salt_version_tagged Version of installed Salt package as a tag",
        "# TYPE salt_version_tagged gauge",
        'salt_version_tagged{{salt_version="{}"}} 1.0'.format(salt.version.__version__),
        "# HELP salt_failed Information regarding state with failure condition",
        "# TYPE salt_failed gauge",
        'salt_failed{state_comment="Command echo includeme run",state_id="echo includeme"} 1.0',
    ]

    # Test one failed state
    expected = "\n".join(sorted(promfile_lines))

    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Drop time-based fields for comparison
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )
    assert salt_prom == expected

    # Test two failed states
    job_ret["return"]["cmd_|-echo applyme_|-echo applyme_|-run"]["result"] = False
    promfile_lines[5] = "salt_states_succeeded 0.0"
    promfile_lines[8] = "salt_states_failed 2.0"
    promfile_lines[17] = "salt_states_success_pct 0.0"
    promfile_lines[20] = "salt_states_failure_pct 100.0"
    promfile_lines.append(
        'salt_failed{state_comment="Command echo applyme run",state_id="echo applyme"} 1.0'
    )
    expected = "\n".join(sorted(promfile_lines))

    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Drop time-based fields for comparison
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )
    assert salt_prom == expected

    # Test abort state ID
    prometheus_textfile.__opts__.update({"abort_state_ids": ["echo includeme"]})
    promfile_lines.extend(
        [
            "# HELP salt_aborted Flag to show that a specific abort state failed",
            "# TYPE salt_aborted gauge",
            "salt_aborted 1.0",
        ]
    )
    expected = "\n".join(sorted(promfile_lines))
    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Drop time-based fields for comparison
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )
    assert salt_prom == expected


def test_fail_comments_lengths(patch_dunders, job_ret, cache_dir, minion):
    prometheus_textfile.__opts__.update({"show_failed_states": True})
    promfile_lines = [
        "# HELP salt_procs Number of salt minion processes running",
        "# TYPE salt_procs gauge",
        "salt_procs 0.0",
        "# HELP salt_states_succeeded Number of successful states in the run",
        "# TYPE salt_states_succeeded gauge",
        "salt_states_succeeded 0.0",
        "# HELP salt_states_failed Number of failed states in the run",
        "# TYPE salt_states_failed gauge",
        "salt_states_failed 2.0",
        "# HELP salt_states_changed Number of changed states in the run",
        "# TYPE salt_states_changed gauge",
        "salt_states_changed 2.0",
        "# HELP salt_states_total Total states in the run",
        "# TYPE salt_states_total gauge",
        "salt_states_total 2.0",
        "# HELP salt_states_success_pct Percent of successful states in the run",
        "# TYPE salt_states_success_pct gauge",
        "salt_states_success_pct 0.0",
        "# HELP salt_states_failure_pct Percent of failed states in the run",
        "# TYPE salt_states_failure_pct gauge",
        "salt_states_failure_pct 100.0",
        "# HELP salt_states_changed_pct Percent of changed states in the run",
        "# TYPE salt_states_changed_pct gauge",
        "salt_states_changed_pct 100.0",
        "# HELP salt_elapsed_time Time spent for all operations during the state run",
        "# TYPE salt_elapsed_time gauge",
        "salt_elapsed_time 13.695",
        "# HELP salt_last_started Estimated time the state run started",
        "# TYPE salt_last_started gauge",
        "# HELP salt_last_completed Time of last state run completion",
        "# TYPE salt_last_completed gauge",
        "# HELP salt_version Version of installed Salt package",
        "# TYPE salt_version gauge",
        "salt_version {}".format(salt.version.__version__),
        "# HELP salt_version_tagged Version of installed Salt package as a tag",
        "# TYPE salt_version_tagged gauge",
        'salt_version_tagged{{salt_version="{}"}} 1.0'.format(salt.version.__version__),
        "# HELP salt_failed Information regarding state with failure condition",
        "# TYPE salt_failed gauge",
        'salt_failed{state_comment="Command echo includeme run",state_id="echo includeme"} 1.0',
        'salt_failed{state_comment="Command echo applyme run",state_id="echo applyme"} 1.0',
    ]

    # Test two failed states with no comment length limit

    prometheus_textfile.__opts__.update({"fail_comment_length": None})

    expected = "\n".join(sorted(promfile_lines))

    job_ret["return"]["cmd_|-echo includeme_|-echo includeme_|-run"]["result"] = False
    job_ret["return"]["cmd_|-echo applyme_|-echo applyme_|-run"]["result"] = False

    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Drop time-based fields for comparison
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )
    assert salt_prom == expected

    promfile_lines = [
        "# HELP salt_procs Number of salt minion processes running",
        "# TYPE salt_procs gauge",
        "salt_procs 0.0",
        "# HELP salt_states_succeeded Number of successful states in the run",
        "# TYPE salt_states_succeeded gauge",
        "salt_states_succeeded 0.0",
        "# HELP salt_states_failed Number of failed states in the run",
        "# TYPE salt_states_failed gauge",
        "salt_states_failed 2.0",
        "# HELP salt_states_changed Number of changed states in the run",
        "# TYPE salt_states_changed gauge",
        "salt_states_changed 2.0",
        "# HELP salt_states_total Total states in the run",
        "# TYPE salt_states_total gauge",
        "salt_states_total 2.0",
        "# HELP salt_states_success_pct Percent of successful states in the run",
        "# TYPE salt_states_success_pct gauge",
        "salt_states_success_pct 0.0",
        "# HELP salt_states_failure_pct Percent of failed states in the run",
        "# TYPE salt_states_failure_pct gauge",
        "salt_states_failure_pct 100.0",
        "# HELP salt_states_changed_pct Percent of changed states in the run",
        "# TYPE salt_states_changed_pct gauge",
        "salt_states_changed_pct 100.0",
        "# HELP salt_elapsed_time Time spent for all operations during the state run",
        "# TYPE salt_elapsed_time gauge",
        "salt_elapsed_time 13.695",
        "# HELP salt_last_started Estimated time the state run started",
        "# TYPE salt_last_started gauge",
        "# HELP salt_last_completed Time of last state run completion",
        "# TYPE salt_last_completed gauge",
        "# HELP salt_version Version of installed Salt package",
        "# TYPE salt_version gauge",
        "salt_version {}".format(salt.version.__version__),
        "# HELP salt_version_tagged Version of installed Salt package as a tag",
        "# TYPE salt_version_tagged gauge",
        'salt_version_tagged{{salt_version="{}"}} 1.0'.format(salt.version.__version__),
        "# HELP salt_failed Information regarding state with failure condition",
        "# TYPE salt_failed gauge",
        'salt_failed{state_comment="Command echo in",state_id="echo includeme"} 1.0',
        'salt_failed{state_comment="Command echo ap",state_id="echo applyme"} 1.0',
    ]

    # Test two failed states with comment length limit of 15

    prometheus_textfile.__opts__.update({"fail_comment_length": 15})

    expected = "\n".join(sorted(promfile_lines))

    job_ret["return"]["cmd_|-echo includeme_|-echo includeme_|-run"]["result"] = False
    job_ret["return"]["cmd_|-echo applyme_|-echo applyme_|-run"]["result"] = False

    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Drop time-based fields for comparison
        salt_prom = "\n".join(
            sorted(
                line[:-1]
                for line in prom_file
                if not line.startswith("salt_last_started")
                and not line.startswith("salt_last_completed")
            )
        )

    assert salt_prom == expected


def test_prometheus_output_with_raw_version(patch_dunders, job_ret, cache_dir, minion):
    expected_version = "3004+12.g557e6cc0fc"
    short_version = expected_version.split("+", maxsplit=1)[0]
    float_version = str(float(short_version))
    prometheus_textfile.__grains__.update({"saltversion": expected_version})

    # raw_version == False
    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Grab only the salt version
        for line in prom_file:
            if line.startswith("salt_version "):
                salt_version = line.split()[1]
            elif line.startswith("salt_version_tagged"):
                expression_pattern = re.compile('salt_version="(.+)"')
                version = expression_pattern.search(line)
                salt_version_tagged = version.groups()[0]

    assert salt_version == float_version
    assert salt_version_tagged == short_version

    # raw_version == True
    prometheus_textfile.__opts__.update({"raw_version": True})
    prometheus_textfile.returner(job_ret)

    with salt.utils.files.fopen(
        os.path.join(cache_dir, "prometheus_textfile", "salt.prom")
    ) as prom_file:
        # Grab only the salt version
        for line in prom_file:
            if line.startswith("salt_version "):
                salt_version = line.split()[1]
            elif line.startswith("salt_version_tagged"):
                expression_pattern = re.compile('salt_version="(.+)"')
                version = expression_pattern.search(line)
                salt_version_tagged = version.groups()[0]

    assert salt_version == float_version
    assert salt_version_tagged == expected_version
