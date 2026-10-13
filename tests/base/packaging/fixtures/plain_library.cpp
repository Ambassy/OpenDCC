/*
 * Copyright Contributors to the OpenDCC project
 * SPDX-License-Identifier: Apache-2.0
 */

#include "opendcc/base/export.h"
#include "opendcc/opendcc.h"

OPENDCC_NAMESPACE_OPEN

extern "C" OPENDCC_API_EXPORT int packaging_test_plain_library()
{
    return 42;
}

OPENDCC_NAMESPACE_CLOSE
