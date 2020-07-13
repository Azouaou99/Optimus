/******************************************************************************
*       SOFA, Simulation Open-Framework Architecture, version 1.0 RC 1        *
*                (c) 2006-2020 MGH, INRIA, USTL, UJF, CNRS                    *
*                                                                             *
* This library is free software; you can redistribute it and/or modify it     *
* under the terms of the GNU Lesser General Public License as published by    *
* the Free Software Foundation; either version 2.1 of the License, or (at     *
* your option) any later version.                                             *
*                                                                             *
* This library is distributed in the hope that it will be useful, but WITHOUT *
* ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or       *
* FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License *
* for more details.                                                           *
*                                                                             *
* You should have received a copy of the GNU Lesser General Public License    *
* along with this library; if not, write to the Free Software Foundation,     *
* Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA.          *
*******************************************************************************
*                               SOFA :: Modules                               *
*                                                                             *
* Authors: The SOFA Team and external contributors (see Authors.txt)          *
*                                                                             *
* Contact information: contact@sofa-framework.org                             *
******************************************************************************/
#define SOFA_COMPONENT_CONSTRAINT_PARDISOCONSTRAINTCORRECTION_CPP

#include "PardisoConstraintCorrection.inl"
#include <sofa/defaulttype/Vec3Types.h>
#include <sofa/core/ObjectFactory.h>


namespace sofa
{

namespace component
{

namespace constraintset
{


using namespace sofa::defaulttype;

SOFA_DECL_CLASS(PardisoConstraintCorrection)

int LinearSolverContactCorrectionClass = core::RegisterObject("")
    .add< PardisoConstraintCorrection<Vec3Types> >()
    .add< PardisoConstraintCorrection<Vec1Types> >()
    .add< PardisoConstraintCorrection<Rigid3Types> >()
    ;


template class SOFA_CONSTRAINT_API PardisoConstraintCorrection<Vec3Types>;
template class SOFA_CONSTRAINT_API PardisoConstraintCorrection<Vec1Types>;
template class SOFA_CONSTRAINT_API PardisoConstraintCorrection<Rigid3Types>;


} // namespace collision

} // namespace component

} // namespace sofa

